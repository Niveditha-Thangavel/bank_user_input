import json
import os
import re
import io
from datetime import date
from contextlib import redirect_stdout
import streamlit as st

# Import the existing single_agent.main (assumes single_agent.py is in same folder)
# Import two_tools to use it
import multi_agent_two_tools as sa

BANK_FILE = "bank_statements.json"
CREDIT_FILE = "credits_loan.json"

CID_REGEX = re.compile(r"^[Cc]\d{3}$")

# --- Storage helpers (same shape as single_agent expects) ---

def load_json_file(path, root_key):
    if os.path.exists(path):
        with open(path, "r") as f:
            try:
                data = json.load(f)
                if root_key in data and isinstance(data[root_key], list):
                    return data
            except Exception:
                pass
    return {root_key: []}


def save_json_file(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# --- UI ---

st.set_page_config(page_title="Loan approval checker", layout="wide")
st.title("Loan approval checker")
st.write("Use this form to create or append customer data. After saving, you can run the agent for the customer from the same UI.")

col_left, col_right = st.columns(2)

with col_left:
    st.header("Customer & Account")
    customer_id = st.text_input("Customer ID (format C101)")
    account_creation_date = st.date_input("Account creation date", value=date(2024,4,1))

    if customer_id and not CID_REGEX.match(customer_id):
        st.error("Customer ID must match format C### (e.g., C101).")

with col_right:
    st.header("Counts")
    tx_count = st.number_input("Number of transactions", min_value=0, max_value=100, value=4, step=1)
    cards_count = st.number_input("Number of credit cards", min_value=0, max_value=10, value=1, step=1)
    loans_count = st.number_input("Number of loans", min_value=0, max_value=10, value=1, step=1)

st.markdown("---")

# Transactions inputs
st.subheader("Transactions")
transactions = []
for i in range(int(tx_count)):
    cols = st.columns([2,1,1,3])
    d = cols[0].date_input(f"Tx {i+1} date", key=f"tx_date_{i}")
    amt = cols[1].number_input(f"Tx {i+1} amount", key=f"tx_amt_{i}", step=0.01, format="%.2f")
    ttype = cols[2].selectbox(f"Tx {i+1} type", options=["credit","debit"], key=f"tx_type_{i}")
    desc = cols[3].text_input(f"Tx {i+1} description", key=f"tx_desc_{i}")
    transactions.append({"date": d.isoformat(), "amount": float(amt), "type": ttype, "description": desc or ""})

st.markdown("---")

# Credit cards inputs
st.subheader("Credit Cards")
credit_cards = []
for cidx in range(int(cards_count)):
    st.markdown(f"**Card {cidx+1}**")
    card_num = st.text_input(f"Card {cidx+1} number", key=f"card_num_{cidx}")
    credit_limit = st.number_input(f"Card {cidx+1} credit_limit", key=f"card_lim_{cidx}", step=1.0, format="%.2f")
    current_balance = st.number_input(f"Card {cidx+1} current_balance", key=f"card_bal_{cidx}", step=1.0, format="%.2f")
    cycles_count = st.number_input(f"Card {cidx+1} billing cycles count", min_value=0, max_value=12, value=1, key=f"card_cycles_count_{cidx}")
    billing_cycles = []
    for cyc in range(int(cycles_count)):
        cols = st.columns(4)
        cs = cols[0].date_input(f"cycle {cyc+1} start", key=f"cs_{cidx}_{cyc}")
        ce = cols[1].date_input(f"cycle {cyc+1} end", key=f"ce_{cidx}_{cyc}")
        amount_due = cols[2].number_input(f"cycle {cyc+1} amount_due", key=f"due_{cidx}_{cyc}", format="%.2f")
        amount_paid = cols[3].number_input(f"cycle {cyc+1} amount_paid", key=f"paid_{cidx}_{cyc}", format="%.2f")
        payment_date = st.date_input(f"cycle {cyc+1} payment_date", key=f"paydate_{cidx}_{cyc}")
        billing_cycles.append({
            "cycle_start": cs.isoformat(),
            "cycle_end": ce.isoformat(),
            "amount_due": float(amount_due),
            "amount_paid": float(amount_paid),
            "payment_date": payment_date.isoformat()
        })
    credit_cards.append({
        "card_number": card_num,
        "credit_limit": float(credit_limit),
        "current_balance": float(current_balance),
        "billing_cycles": billing_cycles
    })

st.markdown("---")

# Loans inputs
st.subheader("Loans")
loans = []
for lidx in range(int(loans_count)):
    st.markdown(f"**Loan {lidx+1}**")
    loan_id = st.text_input(f"Loan {lidx+1} id", key=f"loan_id_{lidx}")
    loan_type = st.text_input(f"Loan {lidx+1} type", key=f"loan_type_{lidx}")
    principal = st.number_input(f"Loan {lidx+1} principal_amount", key=f"loan_pr_{lidx}", format="%.2f")
    outstanding = st.number_input(f"Loan {lidx+1} outstanding_amount", key=f"loan_out_{lidx}", format="%.2f")
    monthly_due = st.number_input(f"Loan {lidx+1} monthly_due", key=f"loan_mon_{lidx}", format="%.2f")
    last_payment = st.date_input(f"Loan {lidx+1} last_payment_date", key=f"loan_last_{lidx}")
    loans.append({
        "loan_id": loan_id,
        "loan_type": loan_type,
        "principal_amount": float(principal),
        "outstanding_amount": float(outstanding),
        "monthly_due": float(monthly_due),
        "last_payment_date": last_payment.isoformat()
    })

st.markdown("---")

# Action buttons
col_save, col_run = st.columns(2)
with col_save:
    if st.button("Save / Append to JSON files"):
        if not customer_id:
            st.error("Please provide a Customer ID before saving.")
        elif not CID_REGEX.match(customer_id):
            st.error("Customer ID must be in the format C### (e.g., C101).")
        else:
            bank_data = load_json_file(BANK_FILE, "bank_statements")
            credit_data = load_json_file(CREDIT_FILE, "customer_accounts")

            bank_entry = {"customer_id": customer_id, "transactions": transactions}
            credit_entry = {
                "customer_id": customer_id,
                "account_creation_date": account_creation_date.isoformat(),
                "credit_cards": credit_cards,
                "loans": loans
            }

            bank_data["bank_statements"].append(bank_entry)
            credit_data["customer_accounts"].append(credit_entry)

            save_json_file(BANK_FILE, bank_data)
            save_json_file(CREDIT_FILE, credit_data)

            st.success(f"Saved data for {customer_id} to {BANK_FILE} and {CREDIT_FILE}.")

with col_run:
    if st.button("Run agent for this Customer ID"):
        if not customer_id:
            st.error("Provide a valid Customer ID (e.g., C101) before running the agent.")
        else:
            prompt = f"my id is {customer_id}"
            # Call single_agent.main which should return a dict-like response when possible
            try:
                raw_resp = sa.main(prompt)
            except Exception as e:
                st.error(f"Agent run failed: {e}")
                raw_resp = None

            # Normalize response to a dict
            resp = None
            if isinstance(raw_resp, dict):
                resp = raw_resp
            elif isinstance(raw_resp, str):
                try:
                    resp = json.loads(raw_resp)
                except Exception:
                    # try to extract JSON-like substring
                    import re as _re
                    m = _re.search(r"\{[\s\S]*\}", raw_resp)
                    if m:
                        try:
                            resp = json.loads(m.group(0))
                        except Exception:
                            resp = None
            elif raw_resp is None:
                resp = None

            if resp is None:
                st.error("Could not parse agent response. The agent may have printed logs. Consider updating single_agent.main to return JSON.")
            else:
                # Decision badge
                decision = resp.get("decision", "UNKNOWN").upper()
                reason = resp.get("reason", "")

                if decision == "APPROVE":
                    st.markdown(f"<h3 style='color: #0f5132; background:#d4edda; padding:8px; border-radius:6px; display:inline-block'>✅ APPROVE</h3>", unsafe_allow_html=True)
                elif decision == "REVIEW":
                    st.markdown(f"<h3 style='color: #664d03; background:#fff3cd; padding:8px; border-radius:6px; display:inline-block'>⚠️ REVIEW</h3>", unsafe_allow_html=True)
                elif decision == "REJECT":
                    st.markdown(f"<h3 style='color: #842029; background:#f8d7da; padding:8px; border-radius:6px; display:inline-block'>❌ REJECT</h3>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<h3 style='background:#e2e3e5; padding:8px; border-radius:6px; display:inline-block'>{decision}</h3>", unsafe_allow_html=True)

                st.write("")

                # Dashboard-like summary
                st.subheader("Decision summary")
                col1, col2, col3 = st.columns([2,2,3])
                with col1:
                    st.write("**Decision**")
                    st.write(f"**{decision}**")
                with col2:
                    st.write("**Customer ID**")
                    st.write(customer_id)
                with col3:
                    st.write("**Reason (short)**")
                    st.write(reason)
                    # simple suggestion heuristics
                    suggestions = []
                    rlow = reason.lower()
                    if "income" in rlow:
                        suggestions.append("Provide pay slips or increase income / add co-applicant.")
                    if "credit" in rlow or "utilis" in rlow or "payment" in rlow:
                        suggestions.append("Pay down credit balances; provide statement of on-time payments.")
                    if "documentation" in rlow or "identity" in rlow:
                        suggestions.append("Upload KYC / identity documents (ID, address proof).")
                    if "loan" in rlow:
                        suggestions.append("Provide loan statements or consolidation plan.")
                    if not suggestions:
                        suggestions.append("No immediate suggestions. Review the agent reason for details.")

                    st.write("**Suggestions**")
                    for s in suggestions:
                        st.markdown(f"- {s}")

                st.markdown("---")

st.markdown("---")
