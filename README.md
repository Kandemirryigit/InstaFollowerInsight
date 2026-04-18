# 📊 InstaFollowerInsight

A Python-based Instagram analytics tool that tracks and analyzes changes in followers and following lists over time.

## 🚀 Overview

**InstaFollowerInsight** is a full-stack automation tool that monitors Instagram accounts by taking snapshots of their followers and following lists. It uses web scraping and data comparison techniques to detect changes between different time intervals.

By comparing snapshots, the system identifies:

* ✅ New followers
* ❌ Unfollowers
* ➕ Newly followed accounts
* ➖ Unfollowed accounts

All processes are automated and accessible through a web interface.

---

## ⚙️ Features

* 📸 Snapshot-based tracking system
* 🔍 Accurate follow/unfollow detection
* 🌐 Web-based dashboard built with Flask
* 🔐 User authentication system (login/register)
* ⚡ Automated scraping using Selenium
* 🧠 Efficient diff comparison algorithm
* 💾 SQLite database for persistent storage
* 📂 Supports multiple usernames or URLs

---

## 🛠️ Technologies Used

* **Backend:** Python, Flask
* **Automation:** Selenium
* **Database:** SQLite3
* **Frontend:** HTML (Jinja Templates)
* **Data Processing:** Pandas

---

## 🧠 How It Works

1. The user logs into the system via the web interface.
2. Selenium automates Instagram login and navigates to the target profile.
3. Followers and following lists are scraped and stored in the SQLite database.
4. Each run creates a new snapshot of the data.
5. The system compares previous and current snapshots using a diff algorithm.
6. Results are displayed on the dashboard.

---

## 🎯 Purpose

This project was built to automate the process of tracking Instagram follower changes over time.  
Instead of manually checking profiles, users can analyze follow/unfollow behavior using stored data snapshots and automated comparison.

---

## ▶️ Usage

1. Start the Flask application:

```bash
python app.py
```

2. Open your browser and go to:

```
http://127.0.0.1:5000/
```

3. Register/Login and start tracking accounts.

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

## 📁 Screenshots
### Login Page
<img width="1916" height="950" alt="Screenshot From 2026-04-18 12-47-47" src="https://github.com/user-attachments/assets/218f5ea3-7c1e-43b1-9ac5-5fe81743241d" />

### Dashboard
<img width="1916" height="950" alt="Screenshot From 2026-04-18 12-51-11" src="https://github.com/user-attachments/assets/39afe78b-e61f-4ba0-96f4-9e14daa4b2d3" />

### Scraping
<img width="1916" height="950" alt="Screenshot From 2026-04-18 12-53-53" src="https://github.com/user-attachments/assets/b56ca536-b255-4e28-938b-8defdcd4d2b3" />

### Compare
<img width="1916" height="950" alt="Screenshot From 2026-04-18 12-52-02" src="https://github.com/user-attachments/assets/f6f09f04-ca2f-4982-8572-1f5324dc9e87" />
















## ⚠️ Disclaimer

This project is for educational purposes only.
Use responsibly and comply with Instagram's terms of service.

---

## 📌 Future Improvements

* Real-time tracking system
* Email/notification alerts
* Data visualization (charts & graphs)
* API integration
* Deployment (Docker / Cloud)

---

## 👤 Author

Yiğit Kandemir

---

## ⭐ Contributing

Pull requests are welcome. For major changes, please open an issue first.

---
