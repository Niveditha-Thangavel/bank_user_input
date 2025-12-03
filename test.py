#This is a sample file to demonstrate the credit scoring model

import json

def load_users():
    with open("credentials.json", "r") as file:
        return json.load(file)["users"]

def login():
    print("----- LOGIN -----")
    username = input("Username: ")
    password = input("Password: ")

    users = load_users()

    for user in users:
        if user["username"] == username and user["password"] == password:
            print("\nLogin successful!\n")
            return True

    print("\nInvalid username or password.\n")
    return False

def credit_decision(customer):
    income = customer["avg_monthly_income"]
    spend = customer["avg_monthly_spend"]
    late = customer["late_payment_count"]
    util = customer["credit_utilization_ratio"]
    age = customer["account_age_months"]
    suspicious = customer["suspicious_transaction_flags"]
    pattern = customer["transaction_pattern"]

    income_spend_ratio = income / spend if spend > 0 else 0

    if (
        late > 3 or
        util > 70 or
        suspicious > 0 or
        income < spend or
        age < 3 or
        pattern["anomaly_flags"] > 0
    ):
        return "REJECT"

    if (
        income_spend_ratio >= 1.5 and
        late <= 1 and
        util <= 40 and
        age >= 12 and
        suspicious == 0 and
        pattern["incoming_to_outgoing_ratio"] >= 1.2
    ):
        return "APPROVE"

    if (
        1.1 <= income_spend_ratio < 1.5 and
        late <= 2 and
        util <= 60 and
        suspicious == 0
    ):
        return "REVIEW"

    return "REJECT"


def load_customers():
    with open("customer_data.json", "r") as file:
        return json.load(file)["customers"]


if not login():
    exit()

customers = load_customers()

print("---- Credit Decision Results ----\n")
for cust in customers:
    decision = credit_decision(cust)
    print(f"Customer {cust['customer_id']} → {decision}")
