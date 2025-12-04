from crewai import Agent, Task, Crew,LLM
from crewai.tools import BaseTool
import json
import os
import re
from typing import Any
import streamlit as st

os.environ["OPENAI_API_KEY"] = "your_openai_api_key_here" 
#API_KEY = "AIzaSyCG3JZiOqvWYmLrGHC9RoSbdnN4OkJVUgo"
API_KEY = "AIzaSyBVoM_S7jMuSje9GB0-Gz6-xMLWxTKt5QQ"
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


DEFAULT_RULES_TEXT = (
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
    "Decision rule (exact mapping):\n"
    "- If number_of_rules_satisfied == 11 -> decision = \"APPROVE\"\n"
    "- If 8 <= number_of_rules_satisfied < 1 -> decision = \"REVIEW\"\n"
    "- If number_of_rules_satisfied < 8 -> decision = \"REJECT\"\n\n"
    "OUTPUT REQUIREMENT: Return exactly the JSON object {\"decision\":\"APPROVE|REVIEW|REJECT\",\"reason\":\"string\"} and NOTHING else."
)

class rules_tool(BaseTool):
    name: str = "Rules provider"
    description: str = "Provides the rule-set text (stored when the tool is created)."
    rules_text: str = DEFAULT_RULES_TEXT
    def _run(self, *args, **kwargs):
        return self.rules_text

    def run(self, *args, **kwargs):
        return self._run(*args, **kwargs)




def create_agent(customer_id: str, rules_text: str = None):
    # instantiate tool objects; rules_text is embedded into the rules_tool instance
    data_fetcher = fetch_tool()
    rules_provider = rules_tool(rules_text=DEFAULT_RULES_TEXT)

    # Clear, explicit goal that instructs the LLM step-by-step and enforces exact output format
    single_agent = Agent(
        role="Fetch-and-Decision Agent",
        goal="first use the data fetcher tool to gather the information then use the rules provider tool to generate the final output",
        backstory=(
            "Coordinator agent: it fetches customer data, reads business rules from the Rules provider tool, "
            "and uses its LLM to evaluate rules. The agent must return only the required JSON."
        ),
        tools=[data_fetcher, rules_provider],
        allow_delegation=False,
        verbose=True,
        llm=ollm
    )
    return single_agent


def create_task(customer_id: str, rules_text: str = None):
    agent = create_agent(customer_id, rules_text=DEFAULT_RULES_TEXT)

    description = (
        f"Coordinator task for customer {customer_id}.\n\n"
        "Instructions for the agent (tool use required):\n"
        " 1) Call the Data fetcher tool with the exact customer_id to retrieve the payload.\n"
        " 2) Call the Rules provider tool (no args) to obtain the exact rules text.\n"
        " 3) Evaluate each rule against the payload. Use exact rule names when referencing them.\n"
        " 4) Count satisfied rules and map to decision: APPROVE (12), REVIEW (8-11), REJECT (<8).\n"
        " 5) Return exactly one JSON object with keys 'decision' and 'reason' and no other text or fields.\n\n"
        "Expected output: {\"decision\":\"APPROVE|REVIEW|REJECT\",\"reason\":\"string\"}\n"
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
        output = extract_result(result)
        return output
