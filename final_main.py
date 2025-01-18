import streamlit as st
import snowflake.connector
import pandas as pd
from datetime import datetime
import json
from snowflake.snowpark import Session



import streamlit as st
from datetime import datetime
import pandas as pd
import json

# Import python packages
import streamlit as st
import pandas as pd
import json
import os



import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os

# We can also use Snowpark for our analyses!
# from snowflake.snowpark.context import get_active_session

# SNOWFLAKE_CONFIG = {
#     "account": "xyb99777",
#     "user": "TESTING",
#     "password": "Harsha123",
#     "warehouse": "ECOMMERCE_WH",
#     "database": "ECOMMERCE_DB",
#     "schema": "PUBLIC"
# }

SNOWFLAKE_CONFIG = {
    "account": "TLB97748",
    "user": "HARSHAVARDHANGOVIND",
    "password": "Harsha_456",
    "warehouse": "ECOMMERCE_WH",
    "database": "ECOMMERCE_DB",
    "schema": "PUBLIC"
}

session = Session.builder.configs(SNOWFLAKE_CONFIG).create()




def get_mistral_query(session, user_query):
    """
    Get Mistral LLM output using SNOWFLAKE.CORTEX.COMPLETE
    
    Args:
        session: Snowpark session object
        user_query: User's query string
    
    Returns:
        str: SQL query generated by Mistral
    """
    try:
        # Define the prompt template
        prompt_template = f"""
        You are an advanced language model designed to understand and transform human queries into structured semantic search queries.
        
        **Task**: Convert the following human query into a concise and relevant query focused on finding similar product titles in the `products` table. The output should preserve the user's intent and be well-suited for similarity comparison with the `TITLE` column.
        
        **Human Query**: {user_query}
        
        **output should only contain the rephrased query nothing else.**
        """
        
        # Define the SQL query to call SNOWFLAKE.CORTEX.COMPLETE
        query = f"""
        SELECT SNOWFLAKE.CORTEX.COMPLETE(
            'mistral-large',
            $${prompt_template}$$
        ) AS response
        """
        
        # Execute the query and collect results
        result = session.sql(query).collect()
        
        # Check if the result is valid
        if not result or len(result) == 0:
            raise ValueError("No response received from Mistral")
        
        # Return the cleaned-up response
        return result[0]["RESPONSE"].strip()
        
    except Exception as e:
        raise Exception(f"Error generating SQL query: {str(e)}")


def fetch_data_from_table(session, sql_query, temp_table_name):
    """
    Executes the query generated by Mistral on the product_table and saves the relevant data to a temporary table.
    """
    # Execute the SQL query and fetch data
    print()
    print(sql_query)
    print()
        
    # Collect the result from the query
    result = session.sql(sql_query).collect()

    # Convert the result to a DataFrame (assuming the result is a list)
    result_df = pd.DataFrame(result)
        
    # Optionally, print the DataFrame to check it
    print("result_df:", result_df)

    # Save the result as a temporary table
    session.write_pandas(
        result_df,
        table_name=temp_table_name,
        overwrite=True  # Ensures the table is replaced if it already exists
    )
        
    print(f"Data saved successfully to the temporary table: {temp_table_name}")

import re

def change_table_name(query, old_table, new_table):
    """
    Changes the table name in the SQL query from old_table to new_table.

    Args:
        query (str): The original SQL query as a string.
        old_table (str): The table name to be replaced.
        new_table (str): The new table name.

    Returns:
        str: The modified SQL query with the new table name.
    """
    # Use regex to replace the old table name with the new table name
    modified_query = re.sub(rf'\b{old_table}\b', new_table, query)
    return modified_query

def construct_context(session, user_id):
    """
    Filters results from the USER_INTERACTION_TABLE and PRODUCT_TABLE based on the user ID, 
    constructs a context table, and returns it as a JSON string.

    Args:
        session: Snowpark session object
        user_id: ID of the user for whom the context is being constructed

    Returns:
        str: A JSON string representation of the context table
    """
    try:
        # Step 1: Create or replace the context table
        create_query = f"""
            CREATE OR REPLACE TABLE CONTEXT_TABLE AS
            SELECT 
                p.*, 
                u.USER_ID, 
                u.INTERACTION_TYPE, 
                u.INTERACTION_TIMESTAMP
            FROM PRODUCT_TABLE p
            JOIN (
                SELECT PRODUCT_ID, USER_ID, INTERACTION_TYPE, INTERACTION_TIMESTAMP
                FROM USER_INTERACTION_TABLE
                WHERE USER_ID = {user_id}
            ) u
            ON p.PRODUCT_ID = u.PRODUCT_ID;
        """
        session.sql(create_query).collect()

        # Step 2: Fetch the updated context table
        results = session.sql("SELECT * FROM CONTEXT_TABLE").to_pandas()

        # Step 3: Convert the DataFrame to JSON
        context = results.to_json(orient="records", lines=False)
        return context

    except Exception as e:
        raise Exception(f"Error constructing and updating context: {str(e)}")


def create_cortex_search_service(session, table_name):
    """
    Creates a Cortex Search Service on the TITLE column with specified attributes.
    
    Args:
        session: The Snowflake session/connection object.

    Returns:
        None
    """
    session.sql(f"""
        CREATE OR REPLACE CORTEX SEARCH SERVICE product_search_service
        ON TITLE
        ATTRIBUTES CATEGORY_1, CATEGORY_2, CATEGORY_3,HIGHLIGHTS, MRP
        WAREHOUSE = ECOMMERCE_wh
        TARGET_LAG = '1 day'
        EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
        AS (
            SELECT
                *
            FROM {table_name}
        );
    """).collect()
    
def save_to_temp_table(session, df: pd.DataFrame, table_name: str = "TEMP_TABLE") -> bool:
    """
    Save DataFrame to a temporary table in Snowflake. Create the table if it does not exist.
    """
    try:
        # Create the table if it does not exist
        columns = ", ".join([f'"{col}" STRING' for col in df.columns])  # Assuming STRING as default data type
        create_query = f"CREATE OR REPLACE TABLE {table_name} ({columns})"
        session.sql(create_query).collect()
        print(f"Temporary table {table_name} created successfully.")
        
        # Replace NaN values with None
        for column in df.columns:
            df[column] = df[column].where(pd.notna(df[column]), None)
        
        # Overwrite existing table data
        session.write_pandas(
            df,
            table_name,
            overwrite=True,
            quote_identifiers=False
        )
        print(f"Results successfully saved to temporary table {table_name}")
        return True
    except Exception as e:
        print(f"Error saving to temporary table: {str(e)}")
        return False


def process_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Process numeric columns in the DataFrame.
    """
    numeric_columns = ['MRP', 'PRODUCT_RATING', 'SELLER_RATING']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df
    
def create_search_config(user_query: str) -> dict:
    """
    Create a search configuration dictionary based on the user query.
    """
    return {
        "query": user_query,
        "columns": [
            "CATEGORY_1", "CATEGORY_2", "CATEGORY_3", "DESCRIPTION",
            "HIGHLIGHTS", "IMAGE_LINKS", "MRP", "PRODUCT_ID", 
            "PRODUCT_RATING", "SELLER_NAME", "SELLER_RATING", "TITLE"
        ],
    }

def build_search_query(search_json: str) -> str:
    """
    Build the SQL query for searching by embedding the JSON search configuration.
    """
    # Ensure the JSON string is correctly escaped
    search_json_escaped = search_json.replace('"', '\\"')
    
    return f"""
    SELECT PARSE_JSON(
        SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
            'ECOMMERCE_DB.PUBLIC.PRODUCT_SEARCH_SERVICE',
            '{search_json_escaped}'  -- Embedding the escaped JSON string
        )
    ) as SEARCH_RESULTS;
    """

def filter_temp_table(session, user_query):
    """
    Main function to process search query, create search configuration, and filter results.
    """
    try:
        # Clean the query if necessary (here, it's just a placeholder)
        cleaned_query = user_query

        # Create the Cortex Search Service (ensure it is created beforehand)
        create_cortex_search_service(session, "TEMP_TABLE")

        # Create search configuration
        search_config = create_search_config(cleaned_query)

        # Convert the search configuration to a JSON string
        search_json = json.dumps(search_config)

        # Debug: Print the search JSON to ensure it's correctly formatted
        print("Debug - Search JSON:", search_json)
        
        # Build the final SQL query using the escaped JSON configuration
        query = build_search_query(search_json)

        # Debug: Print the final query before execution
        print("Debug - Executing query:", query)

        # Execute query
        results = session.sql(query).to_pandas()
        print("Debug - Query results:", results)
        # print("here1")
        
        if results.empty:
            print("No results found")
            return pd.DataFrame()
        
        # Parse results
        parsed_results = results['SEARCH_RESULTS'].iloc[0]
        print("parsed_results:", parsed_results)
        # print("here2")
        
        # Handle string to dict conversion if necessary
        if isinstance(parsed_results, str):
            try:
                parsed_results = json.loads(parsed_results)
            except json.JSONDecodeError:
                print("Error: Could not parse results as JSON")
                return pd.DataFrame()
        
        # Extract results array
        if isinstance(parsed_results, dict) and 'results' in parsed_results:
            search_results = parsed_results['results']
            print("here3")
            print(search_results)
        else:
            print("No results array found in response")
            return pd.DataFrame()
        
        # Convert to DataFrame and process
        flattened_results = pd.json_normalize(search_results)
        if flattened_results.empty:
            print("Search returned no matching results")
            return pd.DataFrame()
        
        # Process numeric columns
        flattened_results = process_numeric_columns(flattened_results)
        
        # Save to temporary table
        if save_to_temp_table(session, flattened_results, "TEMP_TABLE"):
            return flattened_results
        else:
            print("Failed to save results to temporary table")
            return flattened_results
        
    except Exception as e:
        print(f"Error in filter_temp_table: {str(e)}")
        return pd.DataFrame()


def filter_context_table(session, user_query):
    """
    Main function to process search query and filter results.
    """
    try:
        # Clean the query if necessary (here, it's just a placeholder)
        cleaned_query = user_query

        # Create the Cortex Search Service (ensure it is created beforehand)
        create_cortex_search_service(session, "CONTEXT_TABLE")

        # Create search configuration
        search_config = create_search_config(cleaned_query)

        # Convert the search configuration to a JSON string
        search_json = json.dumps(search_config)

        # Debug: Print the search JSON to ensure it's correctly formatted
        print("Debug - Search JSON:", search_json)
        
        # Build the final SQL query using the escaped JSON configuration
        query = build_search_query(search_json)

        # Debug: Print the final query before execution
        print("Debug - Executing query:", query)
        
        # Execute query
        results = session.sql(query).to_pandas()
        # print("Debug - Query results:", results)
        # print("here1")
        
        if results.empty:
            print("No results found")
            return pd.DataFrame()
        
        # Parse results
        parsed_results = results['SEARCH_RESULTS'].iloc[0]
        # print("parsed_results:", parsed_results)
        # print("here2")
        
        # Handle string to dict conversion if necessary
        if isinstance(parsed_results, str):
            try:
                parsed_results = json.loads(parsed_results)
            except json.JSONDecodeError:
                print("Error: Could not parse results as JSON")
                return pd.DataFrame()
        
        # Extract results array
        if isinstance(parsed_results, dict) and 'results' in parsed_results:
            search_results = parsed_results['results']
            print("here3")
            print(search_results)
        else:
            print("No results array found in response")
            return pd.DataFrame()
        
        # Convert to DataFrame and process
        flattened_results = pd.json_normalize(search_results)
        if flattened_results.empty:
            print("Search returned no matching results")
            return pd.DataFrame()
        
        # Process numeric columns
        flattened_results = process_numeric_columns(flattened_results)
        
        # Save to temporary table
        if save_to_temp_table(session, flattened_results, "CONTEXT_TABLE"):
            return flattened_results
        else:
            print("Failed to save results to temporary table")
            return flattened_results
        
    except Exception as e:
        print(f"Error in filter_temp_table: {str(e)}")
        return pd.DataFrame()

def filter_augment_table(session, user_query):
    """
    Main function to process search query and filter results.
    """
    try:
        # Clean the query if necessary (here, it's just a placeholder)
        cleaned_query = user_query

        # Create the Cortex Search Service (ensure it is created beforehand)
        create_cortex_search_service(session, "AUGMENT_TABLE")

        # Create search configuration
        search_config = create_search_config(cleaned_query)

        # Convert the search configuration to a JSON string
        search_json = json.dumps(search_config)

        # Debug: Print the search JSON to ensure it's correctly formatted
        print("Debug - Search JSON:", search_json)
        
        # Build the final SQL query using the escaped JSON configuration
        query = build_search_query(search_json)

        # Debug: Print the final query before execution
        print("Debug - Executing query:", query)
        
        # Execute query
        results = session.sql(query).to_pandas()
        # print("Debug - Query results:", results)
        # print("here1")
        
        if results.empty:
            print("No results found")
            return pd.DataFrame()
        
        # Parse results
        parsed_results = results['SEARCH_RESULTS'].iloc[0]
        # print("parsed_results:", parsed_results)
        # print("here2")
        
        # Handle string to dict conversion if necessary
        if isinstance(parsed_results, str):
            try:
                parsed_results = json.loads(parsed_results)
            except json.JSONDecodeError:
                print("Error: Could not parse results as JSON")
                return pd.DataFrame()
        
        # Extract results array
        if isinstance(parsed_results, dict) and 'results' in parsed_results:
            search_results = parsed_results['results']
            print("here3")
            print(search_results)
        else:
            print("No results array found in response")
            return pd.DataFrame()
        
        # Convert to DataFrame and process
        flattened_results = pd.json_normalize(search_results)
        if flattened_results.empty:
            print("Search returned no matching results")
            return pd.DataFrame()
        
        # Process numeric columns
        flattened_results = process_numeric_columns(flattened_results)

        print(flattened_results)
        
        # Save to temporary table
        if save_to_temp_table(session, flattened_results, "RECOMMENDATIONS_TABLE"):
            return flattened_results
        else:
            print("Failed to save results to temporary table")
            return flattened_results
        
    except Exception as e:
        print(f"Error in filter_temp_table: {str(e)}")
        return pd.DataFrame()


def perform_semantic_search(session, user_id, rank=100, threshold=0.5):
    """
    Performs semantic search and retrieves the top results for a given user.
    
    Args:
        session: The Snowflake session/connection object.
        user_id: The user ID for context filtering (if applicable).
        rank: The number of top results to retrieve (default is 100).
        threshold: The similarity threshold for filtering results (default is 0.5).

    Returns:
        A DataFrame containing the top results.
    """
    try:
        # Step 1: Create a staging table for the product data
        session.sql("""
            CREATE OR REPLACE TABLE product_table_stage AS 
            SELECT * 
            FROM temp_table;
        """).collect()
    
        print("here1")
        # Step 2: Add query embedding vectors for each row in the staging table
        session.sql("""
            ALTER TABLE product_table_stage ADD COLUMN IF NOT EXISTS product_vec VECTOR(FLOAT, 768);
        """).collect()
    
        print("here2")
        # Step 3: Generate embedding vectors for each query in the staging table
        session.sql("""
            UPDATE product_table_stage
            SET product_vec = SNOWFLAKE.CORTEX.EMBED_TEXT_768('snowflake-arctic-embed-m', TITLE);
        """).collect()
    
        print("here3")
        # Step 4: Add query embedding vectors for each row in the context table
        session.sql("""
            ALTER TABLE context_table ADD COLUMN IF NOT EXISTS context_vec VECTOR(FLOAT, 768);
        """).collect()
        print("here4")
    
        # Step 5: Generate embedding vectors for each query in the context table
        session.sql("""
            UPDATE context_table
            SET context_vec = SNOWFLAKE.CORTEX.EMBED_TEXT_768('snowflake-arctic-embed-m', TITLE);
        """).collect()
    
        print("here5")
        # Step 6: Perform semantic search and combine results
        session.sql(f"""
            CREATE OR REPLACE TABLE augment_table AS
            WITH cross_product AS (
                SELECT 
                    p.CATEGORY_1,
                    p.CATEGORY_2,
                    p.CATEGORY_3,
                    p.DESCRIPTION,
                    p.HIGHLIGHTS,
                    p.IMAGE_LINKS,
                    p.MRP,
                    p.PRODUCT_ID,
                    p.PRODUCT_RATING,
                    p.SELLER_NAME,
                    p.SELLER_RATING,
                    p.TITLE,
                    p.product_vec,
                    VECTOR_COSINE_SIMILARITY(c.context_vec, p.product_vec) AS similarity
                FROM context_table c
                CROSS JOIN product_table_stage p
            ),
            ranked_results AS (
                SELECT
                    CATEGORY_1,
                    CATEGORY_2,
                    CATEGORY_3,
                    DESCRIPTION,
                    HIGHLIGHTS,
                    IMAGE_LINKS,
                    MRP,
                    PRODUCT_ID,
                    PRODUCT_RATING,
                    SELLER_NAME,
                    SELLER_RATING,
                    TITLE,
                    similarity
                FROM cross_product
                WHERE similarity > {threshold}
                ORDER BY similarity DESC
            ),
            default_results AS (
                SELECT
                    CATEGORY_1,
                    CATEGORY_2,
                    CATEGORY_3,
                    DESCRIPTION,
                    HIGHLIGHTS,
                    IMAGE_LINKS,
                    MRP,
                    PRODUCT_ID,
                    PRODUCT_RATING,
                    SELLER_NAME,
                    SELLER_RATING,
                    TITLE,
                    NULL as similarity
                FROM product_table_stage
                LIMIT 100
            )
            SELECT *
            FROM (
                SELECT * FROM ranked_results
                UNION ALL
                SELECT * FROM default_results
                WHERE NOT EXISTS (SELECT 1 FROM context_table)
            ) final_results
            ORDER BY similarity DESC NULLS LAST
            LIMIT 100;
        """).collect()
        print("Step 6: Results successfully stored in augment_table.")
    except Exception as e:
        print(f"Error during semantic search: {str(e)}")



def get_recommendations(session, human_query, user_id):
    
    human_query = human_query.replace('"', '').replace("'", "")

    mistral_query = get_mistral_query(session, human_query)
    mistral_query = mistral_query.replace('"', '').replace("'", "")

    print(mistral_query)
    
    context = construct_context(session, user_id)
    print(f"Constructed Context: {context}")

    create_query = f"CREATE OR REPLACE TABLE TEMP_TABLE AS (SELECT * FROM PRODUCT_TABLE)"
    session.sql(create_query).collect()


    print("filter_temp_table\n")
    filter_temp_table(session, mistral_query)

    filter_context_table(session, mistral_query)
    
    print("perform_semantic_search\n")
    perform_semantic_search(session, user_id, rank=1000, threshold=0.0)

    filter_augment_table(session, mistral_query)

    try:
        # Query to fetch data from the specified table
        query = "SELECT * FROM RECOMMENDATIONS_TABLE;"
        
        # Execute the query and convert the result to a pandas DataFrame
        df = session.sql(query).to_pandas()
        
        print("Data successfully fetched from table RECOMMENDATIONS_TABLE.")
        print(df.head())  # Display the first few rows of the DataFrame
        return df
    except Exception as e:
        print(f"Error fetching data from table RECOMMENDATIONS_TABLE': {str(e)}")
        return pd.DataFrame()  # Return an empty DataFrame on error

# df = get_recommendations(session, "I want to buy wedding costume for my marriage", 1)

@st.cache_data(ttl=0)  # Set TTL to 0 to disable caching
def fetch_recommendations(_session, human_query, user_id):
    # Clear any existing tables before running new query
    cleanup_tables(_session)
    return get_recommendations(_session, human_query, user_id)


def cleanup_tables(session):
    """Clean up temporary tables before running new recommendations"""
    cleanup_queries = [
        "DROP TABLE IF EXISTS AUGMENT_TABLE;",
        "DROP TABLE IF EXISTS CONTEXT_TABLE;",
        "DROP TABLE IF EXISTS PRODUCT_TABLE_STAGE;",
        "DROP TABLE IF EXISTS RECOMMENDATIONS_TABLE;",
        "DROP TABLE IF EXISTS TEMP_TABLE;"
    ]
    
    for query in cleanup_queries:
        try:
            session.sql(query).collect()
        except Exception as e:
            print(f"Error cleaning up table: {str(e)}")


def header_section():
    """Create the header section of the application"""
    col1, col2, col3 = st.columns([2,1,1])
    
    with col1:
        st.title("🛍️ Smart Shopping")
    
    with col2:
        user_id = st.number_input("Enter User ID", min_value=0, value=0, step=1, key="user_id_input")
        if user_id > 0:
            st.session_state.user_id = user_id
    
    with col3:
        st.write("🛒 Shopping Cart")
        st.write(f"Items: {len(st.session_state.cart_items)}")
        if st.button("Clear Cart", key="clear_cart_header"):
            st.session_state.cart_items = []
            st.success("Cart cleared!")


# here

import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
import json

def init_session_state():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'cart_items' not in st.session_state:
        st.session_state.cart_items = []
    if 'current_product' not in st.session_state:
        st.session_state.current_product = None
    if 'page' not in st.session_state:
        st.session_state.page = 'home'
    if 'search_performed' not in st.session_state:
        st.session_state.search_performed = False

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_user(session, username, password):
    password_hash = hash_password(password)
    result = session.sql(f"""
        SELECT USER_ID, USERNAME 
        FROM USER_TABLE 
        WHERE USERNAME = '{username}' 
        AND PASSWORD_HASH = '{password_hash}'
    """).collect()
    
    return result[0]['USER_ID'] if result else None

def register_user(session, username, email, password):
    try:
        password_hash = hash_password(password)
        
        # Check for existing user
        existing_user = session.sql(f"""
            SELECT COUNT(*) as count 
            FROM USER_TABLE 
            WHERE USERNAME = '{username}' OR EMAIL = '{email}'
        """).collect()
        
        if existing_user[0]['COUNT'] > 0:
            return "Username or email already exists"
        
        # Insert new user
        session.sql(f"""
            INSERT INTO USER_TABLE (USERNAME, EMAIL, PASSWORD_HASH)
            VALUES ('{username}', '{email}', '{password_hash}')
        """).collect()
        
        return True
        
    except Exception as e:
        return str(e)

def log_interaction(session, user_id, product_id, interaction_type):
    """Log user interaction with products according to the actual table schema"""
    if user_id:
        try:
            current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            session.sql(f"""
                INSERT INTO USER_INTERACTION_TABLE 
                (USER_ID, PRODUCT_ID, INTERACTION_TYPE, INTERACTION_TIMESTAMP)
                VALUES (
                    {user_id},
                    {product_id},
                    '{interaction_type}',
                    '{current_timestamp}'
                )
            """).collect()
        except Exception as e:
            st.error(f"Error logging interaction: {str(e)}")

def record_interaction(session, user_id, product_id, interaction_type):
    try:
        interaction_id = f"INT_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        session.sql(f"""
            INSERT INTO USER_INTERACTIONS
            (INTERACTION_ID, USER_ID, PRODUCT_ID, INTERACTION_TYPE)
            VALUES (
                '{interaction_id}',
                {user_id},
                '{product_id}',
                '{interaction_type}'
            )
        """).collect()
        return True
    except Exception as e:
        st.error(f"Error recording interaction: {str(e)}")
        return False
def get_user_history_products(session, user_id, limit=2):
    """Fetch products from user's interaction history"""
    query = f"""
    SELECT DISTINCT p.*
    FROM PRODUCT_TABLE p
    JOIN USER_INTERACTION_TABLE u ON p.PRODUCT_ID = u.PRODUCT_ID
    WHERE u.USER_ID = {user_id}
    LIMIT {limit}
    """
    return session.sql(query).to_pandas()

def get_random_products(session, limit=8):
    """Fetch random products to fill the remainder"""
    query = f"""
    SELECT *
    FROM PRODUCT_TABLE
    ORDER BY RANDOM()
    LIMIT {limit}
    """
    return session.sql(query).to_pandas()

def display_product_card(product, column, session):
    """Display product card with interaction buttons"""
    with column:
        try:
            st.image(product['IMAGE_LINKS'], use_column_width=True)
        except:
            st.image("https://via.placeholder.com/200", use_column_width=True)
            
        st.markdown(f"**{product['TITLE'][:50]}...**")
        st.write(f"Price: ₹{float(product['MRP']):.2f}")
        st.write(f"Rating: {float(product['PRODUCT_RATING'])}⭐")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("❤️ Like", key=f"like_{product['PRODUCT_ID']}"):
                log_interaction(session, st.session_state.user_id, product['PRODUCT_ID'], 'like')
                st.success("Product liked!")
                
            if st.button("🛒 Add to Cart", key=f"cart_{product['PRODUCT_ID']}"):
                log_interaction(session, st.session_state.user_id, product['PRODUCT_ID'], 'add_to_cart')
                st.success("Added to cart!")
                
        with col2:
            if st.button("👁️ View Details", key=f"view_{product['PRODUCT_ID']}"):
                log_interaction(session, st.session_state.user_id, product['PRODUCT_ID'], 'view')
                st.session_state.current_product = product
                st.session_state.page = 'detail'
                st.rerun()
                
            if st.button("💰 Purchase", key=f"buy_{product['PRODUCT_ID']}"):
                log_interaction(session, st.session_state.user_id, product['PRODUCT_ID'], 'purchase')
                st.success("Purchase successful!")

def display_product_details(product, session):
    """Display detailed product page"""
    st.button("← Back", on_click=lambda: setattr(st.session_state, 'page', 'home'))
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        try:
            st.image(product['IMAGE_LINKS'], width=400)
        except:
            st.image("https://via.placeholder.com/400", width=400)
            
    with col2:
        st.title(product['TITLE'])
        st.markdown("### Product Details")
        st.write(f"**Price:** ₹{float(product['MRP']):.2f}")
        st.write(f"**Rating:** {float(product['PRODUCT_RATING'])}⭐")
        st.write(f"**Seller:** {product['SELLER_NAME']}")
        st.write(f"**Category:** {product['CATEGORY_1']} > {product['CATEGORY_2']} > {product['CATEGORY_3']}")
        
        # Highlights
        st.markdown("### Highlights")
        highlights = json.loads(product['HIGHLIGHTS']) if isinstance(product['HIGHLIGHTS'], str) else product['HIGHLIGHTS']
        if highlights:
            for highlight in highlights:
                st.write(f"• {highlight}")
                
        # Description
        st.markdown("### Description")
        st.write(product['DESCRIPTION'])
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("❤️ Like", key=f"detail_like_{product['PRODUCT_ID']}", use_container_width=True):
                log_interaction(session, st.session_state.user_id, product['PRODUCT_ID'], 'like')
                st.success("Product liked!")
                
        with col2:
            if st.button("🛒 Add to Cart", key=f"detail_cart_{product['PRODUCT_ID']}", use_container_width=True):
                log_interaction(session, st.session_state.user_id, product['PRODUCT_ID'], 'add_to_cart')
                st.success("Added to cart!")
                
        with col3:
            if st.button("💰 Purchase", key=f"detail_buy_{product['PRODUCT_ID']}", use_container_width=True):
                log_interaction(session, st.session_state.user_id, product['PRODUCT_ID'], 'purchase')
                st.success("Purchase successful!")

def main():
    st.set_page_config(page_title="Smart Shopping", layout="wide")
    init_session_state()
    
    if not st.session_state.logged_in:
        auth_page(session)
        return
    
    # Header with logout
    col1, col2 = st.columns([6,1])
    with col1:
        st.title("🛍️ Smart Shopping")
    with col2:
        if st.button("Logout"):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()
    
    # Main content
    if st.session_state.page == 'home':
        # Search bar
        st.markdown("### 🔍 Search Products")
        search_query = st.text_input("", placeholder="What are you looking for today?")
        
        if search_query:
            if st.button("Search"):
                with st.spinner('Searching for products...'):
                    results_df = fetch_recommendations(session, search_query, st.session_state.user_id)
                    if not results_df.empty:
                        st.markdown("### Search Results")
                        for i in range(0, len(results_df), 3):
                            cols = st.columns(3)
                            for j in range(3):
                                if i + j < len(results_df):
                                    display_product_card(results_df.iloc[i + j], cols[j], session)
                    else:
                        st.info("No products found matching your search.")
        
        # Show user history and random products
        else:
            st.markdown("### Based on Your History")
            history_products = get_user_history_products(session, st.session_state.user_id)
            random_products = get_random_products(session, 10 - len(history_products))
            
            # Display all products in 3 columns
            all_products = pd.concat([history_products, random_products])
            for i in range(0, len(all_products), 3):
                cols = st.columns(3)
                for j in range(3):
                    if i + j < len(all_products):
                        display_product_card(all_products.iloc[i + j], cols[j], session)
    
    elif st.session_state.page == 'detail' and st.session_state.current_product:
        display_product_details(st.session_state.current_product, session)

if __name__ == "__main__":
    main()