# 📊 InstaFollowerInsight

A Python-based Instagram analytics tool that tracks and analyzes changes in followers and following lists over time.

## 🚀 Overview

**InstaFollowerInsight** helps you monitor Instagram accounts by taking snapshots of their followers and following lists. By comparing these snapshots at different times, the tool detects:

* ✅ New followers
* ❌ Unfollowers
* ➕ Newly followed accounts
* ➖ Unfollowed accounts

No manual checking — everything is automated and data-driven.

---

## ⚙️ Features

* 📸 Snapshot-based tracking system
* 🔍 Accurate follow/unfollow detection
* 📂 Supports multiple usernames or URLs
* ⚡ Automated scraping with Selenium
* 🧠 Efficient diff comparison logic
* 💾 Local data storage for analysis

---

## 🛠️ Technologies Used

* Python
* Selenium
* Pandas

---

## ▶️ Usage

1. Run the script to collect initial data:

```bash
python main.py
```

2. Run it again later to take a new snapshot.

3. The tool will compare datasets and output:

   * New followers
   * Unfollowers
   * Follow/unfollow changes

---

## 📁 Project Structure

```
InstaFollowerInsight/
│── templates/
│   ├── base.html
│   ├── compare.html
│   ├── dashboard.html
│   ├── login.html
│   ├── register.html
│   ├── running.html
│   ├── snapshot.html
│── instance/
│   ├── tracker.db
│── app.py
│── driver_setup.py
│── login.py
│── models.py
│── scraper.py


```

---

## ⚠️ Disclaimer

This project is for educational purposes only.
Use responsibly and comply with Instagram's terms of service.

---

## 📌 Future Improvements

* Real-time tracking
* Notification system
* Advanced analytics

---

## 👤 Author

Yiğit Kandemir

---

## ⭐ Contributing

Pull requests are welcome. For major changes, please open an issue first.

---
