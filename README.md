# 🪙 Coin Toss Arena

A simple yet interactive **Coin Toss Web Application** built with **Flask** and deployed on AWS.
It helps players decide who goes first using a coin flip, with score tracking and a clean UI.

---

## 🚀 Live Demo

> Deployed on AWS App Runner
> *https://hhjnc22mj9.us-east-1.awsapprunner.com/*

---

## 📌 Features

* 🎯 Coin toss (Heads / Tails)
* 👤 Editable player names
* 🧮 Score tracking (Best of 3)
* 🎉 Confetti effect for winner
* 🔊 Sound effect on toss
* 📱 Fully responsive (mobile-friendly)
* 🎨 Modern UI design

---

## 🛠️ Tech Stack

* **Frontend:** HTML, CSS, JavaScript
* **Backend:** Python (Flask)
* **Server:** Gunicorn
* **Deployment:** AWS App Runner
* **Version Control:** Git & GitHub

---

## 📂 Project Structure

```
coin-toss-app/
│── app.py
│── requirements.txt
│── templates/
│   └── index.html
│── static/
│   └── sound/
│       └── toss.mp3
│── README.md
```

---

## ⚙️ Installation & Run Locally

### 1️⃣ Clone the repo

```bash
git clone https://github.com/Syed-Amjad/coin-toss-app.git
cd coin-toss-app
```

### 2️⃣ Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Run the app

```bash
python app.py
```

👉 Open:

```
http://127.0.0.1:8080
```

---

## ☁️ Deployment (AWS App Runner)

### Configuration used:

**Build Command:**

```bash
pip3 install --target=/app -r requirements.txt
```

**Start Command:**

```bash
python3 -m gunicorn -b 0.0.0.0:8080 app:app
```

---

## 🧠 What I Learned

* Deploying Flask apps on AWS
* Debugging build vs runtime issues
* Handling dependency isolation in App Runner
* Using Gunicorn for production servers
* Understanding cloud deployment workflows

---

## 🔮 Future Improvements

* 🔁 Realistic 3D coin animation
* 📤 Share result via WhatsApp
* 📊 Game history tracking
* 🌐 Custom domain integration

---

## 👨‍💻 Author

**Amjad**
📧 syed.amjad.hashmi@gmail.com
🔗 GitHub: https://github.com/Syed-Amjad

---

## ⭐ Contribute

Feel free to fork, improve, and submit a pull request.

---

## 📄 License

This project is open-source and available under the MIT License.
