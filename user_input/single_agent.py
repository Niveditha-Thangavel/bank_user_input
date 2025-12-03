from crewai import Agent, Task, Crew,LLM
from crewai.tools import BaseTool
import json
import os
import re
from typing import Any

os.environ["OPENAI_API_KEY"] = "your_openai_api_key_here" 
#API_KEY = "AIzaSyCG3JZiOqvWYmLrGHC9RoSbdnN4OkJVUgo"
API_KEY = "AIzaSyAqoKO84yDwnHocfSxLEHKzHyzygNtE2qY"
ollm = LLM(model='gemini/gemini-2.5-flash', api_key=API_KEY)


class fetch_tool(BaseTool):
    name:str = "Data fetcher"
    description:str = "Fetches the right customer account data, from database(json file)"
    def _run(self,customer_id:str):
        with open ("bank_statements.json","r") as f:
            statement = json.load(f)

        with open ("credits_loan.json","r") as f1:
            credit_loan = json.load(f1)

        statement_customer = -1
        account_creation = -1
        credit = -1
        loans = -1

        for id in statement["bank_statements"]:
            if id["customer_id"] == customer_id:
                statement_customer = id["transactions"]

        for id in credit_loan["customer_accounts"]:
            if id["customer_id"] == customer_id:
                account_creation = id["account_creation_date"]
                credit = id["credit_cards"]
                loans = id["loans"]
        data = {"transactions": statement_customer, "account_creation_date":account_creation,"credit_card":credit, "loans":loans}
        return data


def create_agent(customer_id):
    single_agent = Agent(
        role="Fetch-and-Decision Agent",
        goal=(
            f"Use the Data fetcher tool to retrieve {customer_id}'s financial payload. "
            "Evaluate the following 12 rules and determine how many rules are satisfied. "
            "Use the exact rule names when mentioning rules in the reason. "
            "Return ONLY a JSON object with keys 'decision' and 'reason' and no other keys or text."
        ),
        backstory=(
            f"This agent fetches the {customer_id}'s financial data and evaluates the textual rules. "
            "Decision mapping: APPROVE when all 12 rules satisfied; REVIEW when 8-11 rules satisfied; REJECT when fewer than 8 rules satisfied."
        ),
        tools=[fetch_tool()],
        allow_delegation=False,
        llm=ollm
    )
    return single_agent


def create_task(customer_id):
    agent = create_agent(customer_id)

    description = (
        "Fetch the full financial payload for customer " + customer_id + " using the provided Data fetcher tool.\n"
        "Evaluate these rules (use exact names when referencing them in reason):\n\n"
        "Rules:\n"
        "1. Income Check: Income must be ≥ ₹20,000 per month\n"
        "2. Account Age: Account must be ≥ 6 months old\n"
        "3. Payment History: Late payments must be ≤ 2\n"
        "4. Transaction Issues: There must be no transaction anomalies\n"
        "5. Credit Usage: Credit utilization must be < 70%\n"
        "6. Current Loans: Customer must have ≤ 1 active loan\n"
        "7. Income–Spend Health Check: Monthly income must show a clear positive margin over monthly spending\n"
        "8. Transaction Activity Check: Customer should have consistent and healthy transaction activity\n"
        "9. Outlier Behavior Check: There must be no extreme or unexplained large transaction outliers\n"
        "10. Liquidity Buffer Check: Customer should maintain a reasonable financial buffer or savings room\n"
        "11. Credit History Strength: Customer must show reliable and stable historical credit behavior\n"
        "12. Documentation & Identity Check: Customer must have complete and verifiable documentation & identity records\n\n"
        "Decision rule (exact mapping):\n"
        "- If number_of_rules_satisfied == 12 -> decision = \"APPROVE\"\n"
        "- If 8 <= number_of_rules_satisfied < 12 -> decision = \"REVIEW\"\n"
        "- If number_of_rules_satisfied < 8 -> decision = \"REJECT\"\n\n"
        "OUTPUT (exact JSON; no extra fields):\n"
        "Return exactly:\n"
        "{\n"
        "  \"decision\": \"APPROVE\" | \"REVIEW\" | \"REJECT\",\n"
        "  \"reason\": \"<short human-readable reasonning or note 'All Passing'>\"\n"
        "}\n\n"
        "MANDATES:\n"
        "- Use the fetch_tool to get the customer's data.\n"
        "- Evaluate rules qualitatively from the payload.\n"
        "- Return only the exact JSON above (no surrounding text).\n"
    )

    task = Task(
        description=description,
        expected_output='{"decision":"APPROVE|REVIEW|REJECT","reason":"string"}',
        agent=agent
    )

    return task


def handle_prompt(prompt: str) -> Any:
    prompt = prompt or ""
    valid = re.search(r"\b[Cc]\d{3}\b", prompt)
    if valid:
        return valid.group(0).upper()
    near = re.search(r"\b[A-Za-z]\d+\b", prompt)
    if near:
        return "INVALID"
    return None


def extract_result(result):
            # 1. If crew produced a proper dict
            if hasattr(result, "json_dict") and isinstance(result.json_dict, dict):
                return result.json_dict
            
            # 2. If raw JSON is inside result.raw
            if hasattr(result, "raw") and isinstance(result.raw, str):
                try:
                    return json.loads(result.raw)
                except:
                    pass

            # 3. Check tasks_output → usually has final JSON
            if hasattr(result, "tasks_output"):
                for t in result.tasks_output:
                    if hasattr(t, "raw"):
                        raw = t.raw
                        if isinstance(raw, dict):
                            return raw
                        if isinstance(raw, str):
                            try:
                                return json.loads(raw)
                            except:
                                pass

            raise ValueError("Could not extract JSON from CrewOutput")

def main(user_prompt):  
    result = handle_prompt(user_prompt)

    if result is None:
        print("Customer ID missing — please provide your ID (e.g., C101).")
    elif result == "INVALID":
        print("Invalid customer ID. Please provide an ID in the format C101 (C + 3 digits).")
    else:
        customer_id = result
        agent = create_agent(customer_id)
        task = create_task(customer_id)


        crew = Crew(
            agents=[agent],
            tasks=[task],
            verbose=True
        )

        result = crew.kickoff()
        print(result)

main("my id is C101")