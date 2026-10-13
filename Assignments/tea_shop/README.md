# Tea Shop Order Simulator — MySQL Edition

This version updates the supplied project to use MySQL instead of SQLite. It keeps the existing HTML, CSS, JavaScript, order form, async/await flow, callback/Promise demonstrations, and Flask JSON routes.

## 1. Configure MySQL

1. Make sure your MySQL server is running.
2. In this project folder, create a file named `.env`.
3. Copy the settings from `.env.example` into `.env`, then enter your own MySQL password. Do not share or commit `.env`.
4. The app uses the configured database name (default: `f_ass_4`) and automatically creates that database and the `tea_shop_orders` table if they do not exist. The MySQL user must have permission to create databases/tables; otherwise create the database manually and grant table permissions.

Expected `.env` keys:

```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=f_ass_4
```

## 2. Install and run (Windows)

```bat
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## API routes

- `POST /api/orders` — creates an order; returns HTTP 201 and JSON.
- `GET /api/orders` — returns saved orders and reconciles preparation deadlines.
- `GET /api/orders/<id>` — returns one order and its current state.

The MySQL table is `tea_shop_orders`. Order states are updated from the saved `ready_at` deadline when an API status route is called. This lets states recover after browser refreshes and server restarts without relying on a browser timer.

## Test scenarios

- Submit a 6-second order and immediately submit a 2-second order; the 2-second order should become Ready first.
- Enable Simulate failure for one order; it should become Failed while other orders progress.
- Refresh while an order is Preparing; it should retain the correct state.
- In browser DevTools → Network, inspect `POST /api/orders`: a valid request returns HTTP 201 and JSON.
- Enter a one-character name to see validation errors.

## Security note

The `.env` file contains database credentials. Keep it private. The downloadable ZIP intentionally contains `.env.example`, not your actual `.env` credentials.
