"""Seed the SQLite database with sample beneficiary data."""
import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "knowledge/risk.db")


def seed():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    with open("knowledge/schema.sql") as f:
        conn.executescript(f.read())

    # company_registry
    companies = [
        ("GB29NWBK60161331926819", "Acme Consulting Ltd", "2010-03-15", "active", "John Smith, Jane Doe", "up_to_date", "GB"),
        ("GB82WEST12345698765433", "TechFlow Solutions", "2005-06-20", "active", "Alice Johnson, Bob Williams", "up_to_date", "GB"),
        ("GB29NWBK60161399999999", "FastCash Holdings", "2021-01-10", "active", "Unknown Director", "overdue", "GB"),
        ("GB82WEST12345698765500", "Green Energy Partners", "2019-04-22", "active", "Emma Davis", "up_to_date", "GB"),
        ("GB29NWBK60161388888888", "Nova Import Export", "2018-07-14", "active", "Carlos Mendez", "up_to_date", "GB"),
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO company_registry VALUES (?,?,?,?,?,?,?)", companies
    )

    # adverse_media
    media = [
        ("GB29NWBK60161331926819", "Acme Consulting investigated for billing irregularities", "Reuters", "2019-11-20", "low"),
        ("GB29NWBK60161399999999", "FastCash Holdings linked to investment fraud scheme", "BBC News", "2023-05-15", "high"),
        ("GB29NWBK60161399999999", "FastCash director arrested for money laundering", "Financial Times", "2023-08-22", "high"),
        ("GB29NWBK60161388888888", "Nova Import Export under customs investigation", "The Guardian", "2024-01-10", "medium"),
    ]
    conn.executemany(
        "INSERT INTO adverse_media (account_id, headline, source, published_date, severity) VALUES (?,?,?,?,?)",
        media,
    )

    # payment_history
    history = [
        ("GB29NWBK60161331926819", 45, 12500.0, 3, 1, "2024-11-01"),
        ("GB82WEST12345698765433", 312, 8750.0, 12, 0, "2024-11-10"),
        ("GB29NWBK60161399999999", 8, 95000.0, 7, 6, "2024-10-28"),
        ("GB82WEST12345698765500", 41, 10800.0, 4, 0, "2024-11-05"),
        ("GB29NWBK60161388888888", 67, 45000.0, 18, 9, "2024-11-08"),
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO payment_history VALUES (?,?,?,?,?,?)", history
    )

    # sanctions_pep
    sanctions = [
        ("GB29NWBK60161399999999", "FastCash Holdings", "sanctions", "OFAC designation: financial crimes", "2023-09-01"),
        ("GB29NWBK60161388888888", "Carlos Mendez", "pep", "Politically exposed person - former minister", "2022-03-15"),
    ]
    conn.executemany(
        "INSERT INTO sanctions_pep (account_id, name, list_type, reason, listed_date) VALUES (?,?,?,?,?)",
        sanctions,
    )

    conn.commit()
    conn.close()
    print(f"Database seeded at {DB_PATH}")


if __name__ == "__main__":
    seed()
