from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)


# -----------------------------
# CREATE DATABASE TABLES
# -----------------------------
def create_table():
    conn = sqlite3.connect("khata.db")
    cursor = conn.cursor()

    # Customers Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            opening_balance REAL,
            notes TEXT
        )
    """)

    # Payments Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            amount REAL,
            payment_date TEXT,
            method TEXT,
            notes TEXT
        )
    """)

    conn.commit()
    conn.close()


create_table()


# -----------------------------
# HOME PAGE
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")


# -----------------------------
# ADD CUSTOMER
# -----------------------------
@app.route("/add-customer", methods=["GET", "POST"])
def add_customer():

    if request.method == "POST":

        name = request.form["name"]
        phone = request.form["phone"]
        address = request.form["address"]
        opening_balance = int(float(request.form["opening_balance"]))
        notes = request.form["notes"]

        conn = sqlite3.connect("khata.db")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO customers
            (name, phone, address, opening_balance, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (
            name,
            phone,
            address,
            opening_balance,
            notes
        ))

        conn.commit()
        conn.close()

        return redirect("/customers")

    return render_template("add_customer.html")


# -----------------------------
# VIEW ALL CUSTOMERS
# -----------------------------
@app.route("/customers")
def customers():
    search = request.args.get("search", "")

    conn = sqlite3.connect("khata.db")
    cursor = conn.cursor()

    if search:
        cursor.execute("""
            SELECT 
                customers.id,
                customers.name,
                customers.phone,
                customers.opening_balance,
                IFNULL(SUM(payments.amount), 0) AS total_paid,
                customers.opening_balance - IFNULL(SUM(payments.amount), 0) AS closing_balance,
                customers.notes
            FROM customers
            LEFT JOIN payments ON customers.id = payments.customer_id
            WHERE customers.name LIKE ? OR customers.phone LIKE ?
            GROUP BY customers.id
        """, (f"%{search}%", f"%{search}%"))
    else:
        cursor.execute("""
            SELECT 
                customers.id,
                customers.name,
                customers.phone,
                customers.opening_balance,
                IFNULL(SUM(payments.amount), 0) AS total_paid,
                customers.opening_balance - IFNULL(SUM(payments.amount), 0) AS closing_balance,
                customers.notes
            FROM customers
            LEFT JOIN payments ON customers.id = payments.customer_id
            GROUP BY customers.id
        """)

    customers = cursor.fetchall()
    conn.close()

    return render_template("customers.html", customers=customers, search=search)

# -----------------------------
# VIEW SINGLE CUSTOMER
# -----------------------------
@app.route("/view-customer/<int:id>")
def view_customer(id):

    conn = sqlite3.connect("khata.db")
    cursor = conn.cursor()

    # Customer Data
    cursor.execute(
        "SELECT * FROM customers WHERE id = ?",
        (id,)
    )
    customer = cursor.fetchone()

    # Payment History
    cursor.execute("""
        SELECT * FROM payments
        WHERE customer_id = ?
        ORDER BY id DESC
    """, (id,))

    payments = cursor.fetchall()

    # Total Paid
    cursor.execute("""
        SELECT SUM(amount)
        FROM payments
        WHERE customer_id = ?
    """, (id,))

    total_paid = cursor.fetchone()[0]

    if total_paid is None:
        total_paid = 0

    # Remaining Balance
    remaining_balance = customer[4] - total_paid

    conn.close()

    return render_template(
        "view_customer.html",
        customer=customer,
        payments=payments,
        total_paid=total_paid,
        remaining_balance=remaining_balance
    )


# -----------------------------
# ADD PAYMENT
# -----------------------------
@app.route("/add-payment/<int:id>", methods=["GET", "POST"])
def add_payment(id):

    conn = sqlite3.connect("khata.db")
    cursor = conn.cursor()

    if request.method == "POST":

        amount = request.form["amount"]
        payment_date = request.form["payment_date"]
        method = request.form["method"]
        notes = request.form["notes"]

        cursor.execute("""
            INSERT INTO payments
            (customer_id, amount, payment_date, method, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (
            id,
            amount,
            payment_date,
            method,
            notes
        ))

        conn.commit()
        conn.close()

        return redirect(f"/view-customer/{id}")

    cursor.execute(
        "SELECT * FROM customers WHERE id = ?",
        (id,)
    )

    customer = cursor.fetchone()

    conn.close()

    return render_template(
        "add_payment.html",
        customer=customer
    )


# -----------------------------
# EDIT CUSTOMER
# -----------------------------
@app.route("/edit-customer/<int:id>", methods=["GET", "POST"])
def edit_customer(id):

    conn = sqlite3.connect("khata.db")
    cursor = conn.cursor()

    if request.method == "POST":

        name = request.form["name"]
        phone = request.form["phone"]
        address = request.form["address"]
        opening_balance = int(float(request.form["opening_balance"]))
        notes = request.form["notes"]

        cursor.execute("""
            UPDATE customers
            SET name = ?,
                phone = ?,
                address = ?,
                opening_balance = ?,
                notes = ?
            WHERE id = ?
        """, (
            name,
            phone,
            address,
            opening_balance,
            notes,
            id
        ))

        conn.commit()
        conn.close()

        return redirect("/customers")

    cursor.execute(
        "SELECT * FROM customers WHERE id = ?",
        (id,)
    )

    customer = cursor.fetchone()

    conn.close()

    return render_template(
        "edit_customer.html",
        customer=customer
    )


# -----------------------------
# DELETE CUSTOMER
# -----------------------------
@app.route("/delete-customer/<int:id>")
def delete_customer(id):

    conn = sqlite3.connect("khata.db")
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM customers WHERE id = ?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/customers")


# -----------------------------
# RUN APP
# -----------------------------

@app.route("/reports")
def reports():
    conn = sqlite3.connect("khata.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM customers")
    total_customers = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(opening_balance) FROM customers")
    total_credit = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(amount) FROM payments")
    total_paid = cursor.fetchone()[0] or 0

    total_outstanding = total_credit - total_paid

    conn.close()

    return render_template(
        "reports.html",
        total_customers=total_customers,
        total_credit=total_credit,
        total_paid=total_paid,
        total_outstanding=total_outstanding
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)


    