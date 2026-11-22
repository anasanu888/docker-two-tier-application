
import os
import time
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "local-practice-secret")

# Database configuration from environment variables
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "mysql-db"),
    "user": os.getenv("DB_USER", "ticketuser"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "ticketdb"),
    "port": int(os.getenv("DB_PORT", "3306"))
}


# Connect to MySQL with retry
def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def initialize_database():
    for attempt in range(30):
        try:
            connection = get_db_connection()
            cursor = connection.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    description TEXT NOT NULL,
                    priority ENUM('Low', 'Medium', 'High')
                        DEFAULT 'Medium',
                    status ENUM('Open', 'In Progress', 'Resolved')
                        DEFAULT 'Open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            connection.commit()
            cursor.close()
            connection.close()

            print("Database connected and table initialized!")
            return

        except mysql.connector.Error as error:
            print(f"Database connection attempt {attempt + 1}: {error}")
            time.sleep(2)

    raise RuntimeError("Could not connect to MySQL after 30 attempts")


# Home page - display tickets
@app.route("/")
def home():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM tickets ORDER BY created_at DESC")
    tickets = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template("index.html", tickets=tickets)


# Create a new ticket
@app.route("/create", methods=["POST"])
def create_ticket():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    priority = request.form.get("priority", "Medium")

    if not title or not description:
        flash("Title and description are required.", "error")
        return redirect(url_for("home"))

    if priority not in ["Low", "Medium", "High"]:
        flash("Invalid priority.", "error")
        return redirect(url_for("home"))

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO tickets (title, description, priority)
        VALUES (%s, %s, %s)
        """,
        (title, description, priority)
    )

    connection.commit()
    cursor.close()
    connection.close()

    flash("Ticket created successfully!", "success")
    return redirect(url_for("home"))


# Update ticket status
@app.route("/update/<int:ticket_id>", methods=["POST"])
def update_ticket(ticket_id):
    status = request.form.get("status")

    if status not in ["Open", "In Progress", "Resolved"]:
        flash("Invalid status.", "error")
        return redirect(url_for("home"))

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        "UPDATE tickets SET status = %s WHERE id = %s",
        (status, ticket_id)
    )

    connection.commit()
    cursor.close()
    connection.close()

    flash("Ticket status updated!", "success")
    return redirect(url_for("home"))


# Delete ticket
@app.route("/delete/<int:ticket_id>", methods=["POST"])
def delete_ticket(ticket_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM tickets WHERE id = %s", (ticket_id,))

    connection.commit()
    cursor.close()
    connection.close()

    flash("Ticket deleted!", "success")
    return redirect(url_for("home"))


# Application health endpoint
@app.route("/health")
def health():
    try:
        connection = get_db_connection()
        connection.close()
        return {"status": "healthy", "database": "connected"}, 200
    except mysql.connector.Error:
        return {"status": "unhealthy", "database": "disconnected"}, 503


if __name__ == "__main__":
    initialize_database()
    app.run(host="0.0.0.0", port=5000)

