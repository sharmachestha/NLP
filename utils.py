from langchain.schema import  OutputParserException
from langchain.chains import LLMChain
from langchain.tools import BaseTool
from langchain.prompts import PromptTemplate
from sqlalchemy.engine.url import URL
from langchain.sql_database import SQLDatabase
from langchain.chat_models import AzureChatOpenAI
from langchain.agents import AgentExecutor
from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from azure.identity import InteractiveBrowserCredential
from azure.keyvault.secrets import SecretClient

try:
    from prompts import (
                           MSSQL_AGENT_PREFIX, 
                          MSSQL_AGENT_FORMAT_INSTRUCTIONS)
except Exception as e:
    print(e)
    from prompts import (
                           MSSQL_AGENT_PREFIX, 
                          MSSQL_AGENT_FORMAT_INSTRUCTIONS)


def run_agent(question:str, agent_chain: AgentExecutor) -> str:
    """Function to run the brain agent and deal with potential parsing errors"""
    
    try:
        return agent_chain.run(input=question)
    
    except OutputParserException as e:
        # If the agent has a parsing error, we use OpenAI model again to reformat the error and give a good answer
        chatgpt_chain = LLMChain(
                llm=agent_chain.agent.llm_chain.llm, 
                    prompt=PromptTemplate(input_variables=["error"],template='Remove any json formating from the below text, also remove any portion that says someting similar this "Could not parse LLM output: ". Reformat your response in beautiful Markdown. Just give me the reformated text, nothing else.\n Text: {error}'), 
                verbose=False
            )

        response = chatgpt_chain.run(str(e))
        return response
    

######## TOOL CLASSES #####################################
###########################################################
    
        
        
class SQLDbTool(BaseTool):
    """Tool SQLDB Agent"""
    
    name = "@DSR"
    description = "useful when the questions includes the term: @DSR.\n"

    llm: AzureChatOpenAI
    
    def _run(self, query: str) -> str:

        # Tenant ID for the Azure Active Directory
        #tenant_id = 'e0ba10c6-0511-4b52-82db-1c4d73100e59'

        # Key Vault details 
        key_vault_name = 'eus2-openaivulcan-kv'
        vault_url = f"https://eus2-openaivulcan-kv.vault.azure.net/"

        # Create an instance of InteractiveBrowserCredential
        #        credential = InteractiveBrowserCredential(tenant_id=tenant_id)

        credential = DefaultAzureCredential()

        # Authenticate using user credentials
        # This will open a browser window prompting the user to log in
        # and grant access to the application
        
        client = SecretClient(vault_url, credential)

        # Access Key Vault secrets
        secret_name = 'source-igdw-sql-pw'
        retrieved_secret = client.get_secret(secret_name).value

        #print(f"Retrieved secret '{secret_name}': {retrieved_secret.value}")

        # Update db_config with dynamic username and password
        db_config = {
        'drivername': 'mssql+pyodbc',
        'username': "AIUser",
        'password': retrieved_secret,
        'host': "AZ-IGDWPRD-01",
        'port': 1433,
        'database': "IGDW",
        'query': {'driver': 'ODBC Driver 17 for SQL Server'}
        # other configurations...
        }

        db_url = URL.create(**db_config)
        db = SQLDatabase.from_uri(db_url)
        toolkit = SQLDatabaseToolkit(db=db, llm=self.llm)
        agent_executor = create_sql_agent(
            prefix=MSSQL_AGENT_PREFIX,
            format_instructions = MSSQL_AGENT_FORMAT_INSTRUCTIONS,
            llm=self.llm,
            toolkit=toolkit,
            callback_manager=self.callbacks,
            verbose=self.verbose
        )

        try:
            response = agent_executor.run(query) 
        except Exception as e:
            response = str(e)

        return response
        
    
    
        
        
        
