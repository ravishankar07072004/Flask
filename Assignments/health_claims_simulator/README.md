# Health Insurance Claims Processing Simulator

A learning project built with Flask, Flask-SQLAlchemy ORM, MySQL, Flask-Login, Flask-WTF CSRF protection, Bootstrap and Jinja templates. All people, policies, hospitals, amounts and decisions are synthetic. This app does not make real insurance decisions or transfer money.

## Features included

- Seeded role-based login: policyholder, hospital desk, claims officer and administrator.
- SQLAlchemy ORM models for users, hospitals, plans, policies, members, claims, checklist metadata, claim history and simulated settlements.
- Synthetic dataset import from the supplied ZIP archive.
- Policy/member/hospital/date/amount validation on claim creation.
- Record-level authorization in Flask routes, not just hidden interface controls.
- Claim state transitions with status history, review assignment, more-information cycle, approval/rejection reason and simulated payout.
- Decimal-based payout formula, combined claim filters, dashboards, policy views and reports.
- Jinja template inheritance, Bootstrap responsive UI, separate CSS/JS and CSRF protection.

## 1. Requirements

- Python 3.10 or newer
- MySQL Server 8.x (or compatible MySQL)
- A MySQL user allowed to create/use the project database

## 2. Create the MySQL database

Open MySQL Workbench or the MySQL command line and run:

```sql
CREATE DATABASE health_claims_simulator
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

The Flask-SQLAlchemy ORM creates the tables. You do not need to write table CREATE statements manually.

## 3. Install and configure

Windows Command Prompt, from this project folder:

```bat
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` with your own MySQL password and a long random `SECRET_KEY`. Never commit `.env` to GitHub.

Example local settings:

```env
SECRET_KEY=replace-with-a-long-random-secret
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=health_claims_simulator
```

## 4. Create tables and import synthetic data

```bat
flask --app run.py init-db
flask --app run.py seed-demo
```

The seed command imports records in foreign-key order from `data/synthetic_dataset.zip`. It skips seeding if a user already exists, so it will not duplicate records. To start over, back up anything you need, drop and recreate the local database, then run both commands again.

## 5. Start the app

```bat
py run.py
```

Open <http://127.0.0.1:5000>.

## Demo accounts

Every seeded account uses the same local demo password `Demo123!` after running the seed command. These are for local classroom use only. Change passwords before any deployment.

| Role | Username |
|---|---|
| Policyholder | `aasha` |
| Policyholder | `bilal` |
| Hospital desk | `city_hospital` |
| Hospital desk | `lotus_hospital` |
| Claims officer | `officer_meera` |
| Claims officer | `officer_rahul` |
| Administrator | `admin_demo` |

Other seeded users are listed in the supplied dataset README/CSV files.


## Administrator: create users and policies

Sign in with an account whose role is `admin`, then open **Admin Manage** in the navigation (or visit `/admin/manage`). This page is protected by a server-side administrator role check.

- **Create User Account:** create a policyholder, hospital desk, claims officer, or administrator. Usernames must be unique, initial passwords must be at least 8 characters, and passwords are stored as Werkzeug password hashes. Hospital desk accounts must be linked to an existing hospital.
- **Create Insurance Policy:** select an existing policyholder and plan, enter coverage dates, and select the status. The end date cannot be before the start date.
- The **Policies** page has an **Add Policy** shortcut for administrators.

The current `users` model supports display name, username, password, role and linked hospital; it does not include email, phone, or address fields. Those would require a model/schema update if needed. New policy creation does not automatically add a covered member; members remain separate records linked to a policy.

## Workflow to demonstrate

1. Log in as `aasha`; open Policies and Claims. Create a reimbursement draft, update checklist metadata and submit.
2. Log in as `city_hospital`; create a cashless claim for CityCare Hospital. Try another hospital ID by modifying a request to verify server-side validation.
3. Log in as `officer_meera`; open a submitted claim, assign it to yourself, and request more information or approve/reject with a reason.
4. Log in as the claim creator; update the checklist and submit the more-info response.
5. Log in as `admin_demo`; open an approved claim and record a simulated settlement.
6. Verify claim history, reports, combined filters, and access denial when trying another policyholder's claim URL.

## ORM structure

- `app/models/`: database entities and SQLAlchemy relationships.
- `app/routes/`: authentication, dashboard, claim workflow, policies and reports.
- `app/services.py`: status transitions, access helper, cover estimate and payout formula.
- `app/seed.py`: CSV import from the supplied ZIP.
- `app/templates/`: Jinja pages, including claim list/detail/create.
- `app/static/`: CSS and JavaScript.
- `app/config.py`: database URI and application configuration.

`db.session.add()` stages ORM objects, `db.session.commit()` persists them, and `db.session.rollback()` cancels a failed transaction. Model relationships let the templates access values such as `claim.member.display_name` without manually writing JOIN statements.

## Important limitations / next development steps

This is a functional starter implementation, not a production insurance platform. Before submission, test all roles and edge cases. Recommended next steps are: add automated pytest tests, add optimistic locking/row locking for officer assignment and settlement concurrency, improve document checklist audit events, add admin reference-data CRUD, and add a production deployment configuration. The project intentionally stores checklist metadata only, not real medical documents.


## Existing-user policy members update

This version lets an administrator select existing policyholder user accounts as policy members. If you already have a `health.members` table, apply this one-time MySQL schema update before starting the updated app:

```sql
USE health;
ALTER TABLE members ADD COLUMN user_id INT NULL;
CREATE INDEX ix_members_user_id ON members (user_id);
ALTER TABLE members ADD CONSTRAINT fk_members_user_id_users
  FOREIGN KEY (user_id) REFERENCES users(id);
```

If your database already has a `user_id` column or index/constraint with these names, skip the corresponding statement. Existing legacy member rows remain readable; newly selected members link to existing user accounts. Do not drop or recreate the database.

## Updated claim workflow and database migration

The updated claim workflow is:

`draft → submitted → hospital_check → policy_check → in_review → approved → paid`

At the hospital and policy checks, the assigned claims officer can reject with a written reason. During `in_review`, the officer can request more information, approve within the requested amount and available cover, or reject with a written reason. The original submitter can respond to `more_info`, returning the claim to `submitted`. `rejected` and `paid` are terminal states.

**If you are updating an existing MySQL database**, back it up first, then extend the MySQL `claims.status` enum so it accepts the two new states. Run this statement once if your database still has the old enum:

```sql
ALTER TABLE claims
MODIFY COLUMN status ENUM(
  'draft', 'submitted', 'hospital_check', 'policy_check',
  'in_review', 'more_info', 'approved', 'rejected', 'paid'
) NOT NULL DEFAULT 'draft';
```

The claim application form now accepts the policy number as a text input (for example `101` or `#101`). Use the policy ID displayed on the Policies page. The server still validates that the policy exists and that the selected member belongs to it.

## SQL schema and claim history trigger

The SQL script is available at `database/schema.sql`. It creates the `health_claims_simulator` database and defines `trg_claim_after_insert`, which automatically inserts the initial claim status into `claim_history` when a row is inserted into `claims`.

**Run order:** First configure `.env` and initialize the Flask database so the `claims` and `claim_history` tables exist. Then run `database/schema.sql` in MySQL Workbench. The script selects `health_claims_simulator`; if your application is configured to use another database (for example, `health`), change the database name in the SQL file to match `DB_NAME` before running it.

This trigger records only the initial claim-history row. It does not record later status changes. If the Flask application already inserts an initial `ClaimHistory` row in its claim-creation code, disable that ORM insert before enabling the trigger to avoid duplicate history entries.
