import queue
import threading
from flask import Flask, render_template, request, redirect, url_for, flash, Response, stream_with_context, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, bcrypt, User, Snapshot, Follower
from driver_setup import create_driver
from login import login as instagram_login
from scraper import scrape_following, scrape_followers, ScrapeError

app = Flask(__name__)
app.config["SECRET_KEY"] = "gizli-anahtar-bunu-degistir"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tracker.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
bcrypt.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "auth_login"
login_manager.login_message = "Lütfen önce giriş yapın."

# {
#   user_id: {
#     "queue":          Queue,
#     "history":        [(msg, pct)],
#     "done":           bool,
#     "phase":          "analyzing" | "waiting" | "scraping" | "finished",
#     "confirm":        threading.Event,
#     "stop":           None | "save" | "discard",
#     "collected":      [],
#     "profile_info":   {"count": int|None, "account": str},
#   }
# }
bot_sessions = {}

@app.template_filter('datetimeformat')
def datetimeformat(value):
    return value.strftime('%d.%m.%Y %H:%M')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()


# ── AUTH ──────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("auth_login"))


@app.route("/register", methods=["GET", "POST"])
def auth_register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        if not username or not email or not password:
            flash("Tüm alanlar zorunludur.", "error")
        elif len(password) < 6:
            flash("Şifre en az 6 karakter olmalıdır.", "error")
        elif password != confirm:
            flash("Şifreler eşleşmiyor.", "error")
        elif User.query.filter_by(username=username).first():
            flash("Bu kullanıcı adı zaten alınmış.", "error")
        elif User.query.filter_by(email=email).first():
            flash("Bu email zaten kayıtlı.", "error")
        else:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Kayıt başarılı, hoş geldiniz!", "success")
            return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def auth_login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password   = request.form.get("password", "")

        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier.lower())
        ).first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            return redirect(url_for("dashboard"))
        else:
            flash("Kullanıcı adı/email veya şifre hatalı.", "error")

    return render_template("login.html")


@app.route("/logout")
@login_required
def auth_logout():
    logout_user()
    return redirect(url_for("auth_login"))


# ── DASHBOARD ─────────────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    snapshots = (
        Snapshot.query
        .filter_by(user_id=current_user.id)
        .order_by(Snapshot.taken_at.desc())
        .all()
    )
    return render_template("dashboard.html", snapshots=snapshots)


# ── BOT ÇALIŞTIR ──────────────────────────────────────────────────────────────

@app.route("/run", methods=["POST"])
@login_required
def run_bot():
    ig_username     = request.form.get("ig_username", "").strip()
    ig_password     = request.form.get("ig_password", "")
    looking_account = request.form.get("looking_account", "").strip()
    scrape_type     = request.form.get("scrape_type", "following")

    if scrape_type not in ("following", "followers"):
        scrape_type = "following"

    if not ig_username or not ig_password or not looking_account:
        flash("Tüm alanlar zorunludur.", "error")
        return redirect(url_for("dashboard"))

    user_id       = current_user.id
    q             = queue.Queue()
    confirm_event = threading.Event()

    bot_sessions[user_id] = {
        "queue":        q,
        "history":      [],
        "done":         False,
        "phase":        "analyzing",
        "confirm":      confirm_event,
        "stop":         None,
        "collected":    [],
        "profile_info": {"count": None, "account": looking_account},
    }

    def bot_thread():
        with app.app_context():
            driver = create_driver()

            def qput(msg, pct):
                item = (msg, pct)
                bot_sessions[user_id]["history"].append(item)
                q.put(item)

            def should_stop():
                return bot_sessions[user_id]["stop"] is not None

            try:
                # ── PHASE 1: Giriş + Profil Analizi ──────────────────────────
                bot_sessions[user_id]["phase"] = "analyzing"

                qput("Instagram'a giriş yapılıyor...", 30)
                instagram_login(driver, ig_username, ig_password)
                qput("Giriş başarılı!", 60)

                qput("Profil bilgileri alınıyor...", 80)
                from scraper import _load_profile_and_get_count
                link_keyword = "/followers/" if scrape_type == "followers" else "/following/"
                count = _load_profile_and_get_count(driver, looking_account, link_keyword)

                bot_sessions[user_id]["profile_info"]["count"] = count
                count_str = f"{count:,}".replace(",", ".") if count else "?"
                qput(f"READY|{count_str}", 100)  # özel sinyal: analiz bitti

                # ── PHASE 2: Kullanıcı onayını bekle ─────────────────────────
                bot_sessions[user_id]["phase"] = "waiting"
                confirmed = confirm_event.wait(timeout=300)  # 5 dakika bekle

                if not confirmed:
                    qput("Zaman aşımı. Tarama iptal edildi.", -1)
                    return

                if bot_sessions[user_id]["stop"] == "discard":
                    qput("⛔ Tarama iptal edildi.", -2)
                    return

                # ── PHASE 3: Tarama ───────────────────────────────────────────
                bot_sessions[user_id]["phase"] = "scraping"
                qput("Tarama başlıyor...", 5)

                def on_progress(msg, pct):
                    qput(msg, pct)

                if scrape_type == "followers":
                    users = scrape_followers(
                        driver, looking_account,
                        progress_callback=on_progress,
                        stop_flag=lambda: should_stop(),
                        collected_ref=bot_sessions[user_id]["collected"]
                    )
                else:
                    users = scrape_following(
                        driver, looking_account,
                        progress_callback=on_progress,
                        stop_flag=lambda: should_stop(),
                        collected_ref=bot_sessions[user_id]["collected"]
                    )

                stop_action = bot_sessions[user_id]["stop"]
                if stop_action == "discard":
                    qput("⛔ Tarama iptal edildi, veriler kaydedilmedi.", -2)
                else:
                    save_users = users if users else bot_sessions[user_id]["collected"]
                    qput(f"Veriler kaydediliyor... ({len(save_users)} kişi)", 92)

                    snapshot = Snapshot(
                        user_id=user_id,
                        target_instagram=looking_account,
                        scrape_type=scrape_type
                    )
                    db.session.add(snapshot)
                    db.session.flush()

                    db.session.bulk_save_objects([
                        Follower(snapshot_id=snapshot.id, instagram_username=u)
                        for u in save_users
                    ])
                    db.session.commit()

                    if stop_action == "save":
                        qput(f"💾 Erken kaydedildi! {len(save_users)} kişi kaydedildi.", 100)
                    else:
                        qput(f"✅ Tamamlandı! {len(save_users)} kişi kaydedildi.", 100)

            except ScrapeError as e:
                db.session.rollback()
                qput(str(e), -1)
            except Exception as e:
                db.session.rollback()
                qput("Beklenmedik bir hata oluştu. Lütfen tekrar dene.", -1)
                print(f"Bot hatası: {e}")
            finally:
                driver.quit()
                bot_sessions[user_id]["done"] = True
                q.put(None)

    thread = threading.Thread(target=bot_thread, daemon=True)
    thread.start()

    type_label = "Takipçiler" if scrape_type == "followers" else "Takip Ettikleri"
    return render_template("running.html", looking_account=looking_account, type_label=type_label)


# ── TARAMAYI ONAYLA ───────────────────────────────────────────────────────────

@app.route("/confirm", methods=["POST"])
@login_required
def confirm_scrape():
    user_id = current_user.id
    session = bot_sessions.get(user_id)
    if not session:
        return jsonify({"ok": False, "msg": "Aktif oturum yok."})
    session["confirm"].set()
    return jsonify({"ok": True})


# ── DURDUR ────────────────────────────────────────────────────────────────────

@app.route("/stop", methods=["POST"])
@login_required
def stop_bot():
    user_id = current_user.id
    action  = request.form.get("action", "discard")

    session = bot_sessions.get(user_id)
    if not session or session["done"]:
        return jsonify({"ok": False, "msg": "Aktif tarama yok."})

    session["stop"] = action

    # Onay bekliyorsa confirm event'ini de tetikle
    if session["phase"] == "waiting":
        session["confirm"].set()

    return jsonify({"ok": True, "action": action})


# ── SSE PROGRESS ──────────────────────────────────────────────────────────────

@app.route("/progress")
@login_required
def progress_stream():
    user_id = current_user.id

    def generate():
        session = bot_sessions.get(user_id)
        if not session:
            yield "data: done\n\n"
            return

        for msg, pct in session["history"]:
            yield f"data: {pct}|{msg}\n\n"

        if session["done"]:
            yield "data: done\n\n"
            return

        q = session["queue"]
        while True:
            item = q.get()
            if item is None:
                yield "data: done\n\n"
                break
            msg, pct = item
            yield f"data: {pct}|{msg}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


# ── SNAPSHOT DETAY ────────────────────────────────────────────────────────────

@app.route("/snapshot/<int:snapshot_id>")
@login_required
def snapshot_detail(snapshot_id):
    snapshot = Snapshot.query.filter_by(id=snapshot_id, user_id=current_user.id).first_or_404()
    return render_template("snapshot.html", snapshot=snapshot)


# ── KARŞILAŞTIRMA ─────────────────────────────────────────────────────────────

@app.route("/compare", methods=["GET", "POST"])
@login_required
def compare():
    snapshots = (
        Snapshot.query
        .filter_by(user_id=current_user.id)
        .order_by(Snapshot.taken_at.desc())
        .all()
    )

    from collections import defaultdict
    grouped_raw = defaultdict(lambda: {"following": [], "followers": []})
    for s in snapshots:
        grouped_raw[s.target_instagram][s.scrape_type].append(s)

    grouped = {}
    for account, types in grouped_raw.items():
        grouped[account] = {
            "following": [
                {"id": s.id, "date": s.taken_at.strftime("%d.%m.%Y %H:%M"), "count": s.follower_count()}
                for s in types["following"]
            ],
            "followers": [
                {"id": s.id, "date": s.taken_at.strftime("%d.%m.%Y %H:%M"), "count": s.follower_count()}
                for s in types["followers"]
            ],
        }

    result = None
    if request.method == "POST":
        id_a = request.form.get("snapshot_a", type=int)
        id_b = request.form.get("snapshot_b", type=int)

        snap_a = Snapshot.query.filter_by(id=id_a, user_id=current_user.id).first()
        snap_b = Snapshot.query.filter_by(id=id_b, user_id=current_user.id).first()

        if not snap_a or not snap_b:
            flash("Geçersiz snapshot seçimi.", "error")
        elif id_a == id_b:
            flash("Aynı snapshot'ı karşılaştıramazsın.", "error")
        else:
            set_a = snap_a.follower_set()
            set_b = snap_b.follower_set()
            same_target = snap_a.target_instagram == snap_b.target_instagram
            types = {snap_a.scrape_type, snap_b.scrape_type}

            if not same_target:
                result = {
                    "mode":       "diff_accounts",
                    "mode_label": "Ortak Kişiler",
                    "snap_a":     snap_a,
                    "snap_b":     snap_b,
                    "mutual":     sorted(set_a & set_b),
                    "selected_a": id_a,
                    "selected_b": id_b,
                }
            elif len(types) == 1:
                scrape_type = snap_a.scrape_type
                if scrape_type == "following":
                    new_label     = "Yeni Takip Ettikleri"
                    removed_label = "Takipten Çıktıkları"
                else:
                    new_label     = "Yeni Takipçiler"
                    removed_label = "Takipten Çıkanlar"
                result = {
                    "mode":           "same",
                    "mode_label":     "Zaman Karşılaştırması",
                    "snap_a":         snap_a,
                    "snap_b":         snap_b,
                    "added":          sorted(set_b - set_a),
                    "removed":        sorted(set_a - set_b),
                    "stayed":         len(set_a & set_b),
                    "new_label":      new_label,
                    "removed_label":  removed_label,
                    "selected_a":     id_a,
                    "selected_b":     id_b,
                }
            else:
                if snap_a.scrape_type == "following":
                    set_following = set_a
                    set_followers = set_b
                else:
                    set_following = set_b
                    set_followers = set_a
                result = {
                    "mode":            "cross",
                    "mode_label":      "Takip Analizi",
                    "snap_a":          snap_a,
                    "snap_b":          snap_b,
                    "mutual":          sorted(set_following & set_followers),
                    "only_followers":  sorted(set_followers - set_following),
                    "only_following":  sorted(set_following - set_followers),
                    "selected_a":      id_a,
                    "selected_b":      id_b,
                }

    return render_template("compare.html", snapshots=snapshots, grouped=grouped, result=result)


# ── SNAPSHOT SİL ──────────────────────────────────────────────────────────────

@app.route("/snapshot/<int:snapshot_id>/delete", methods=["POST"])
@login_required
def delete_snapshot(snapshot_id):
    snapshot = Snapshot.query.filter_by(id=snapshot_id, user_id=current_user.id).first_or_404()
    db.session.delete(snapshot)
    db.session.commit()
    flash("Snapshot silindi.", "success")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True, threaded=True,port=5000)