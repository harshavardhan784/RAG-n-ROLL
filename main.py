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
        
        st.write("here1")
        # Execute the query and collect results
        result = execute_query(session, query)
        st.write("here2")
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
    result = execute_query(session, sql_query)

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
        execute_query(session, create_query)

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
    execute_query(session, f"""
        CREATE OR REPLACE CORTEX SEARCH SERVICE product_search_service
        ON TITLE
        ATTRIBUTES CATEGORY_1, CATEGORY_2, CATEGORY_3,HIGHLIGHTS, MRP
        WAREHOUSE = ECOMMERCE_wh
        TARGET_LAG = '1 hour'
        EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
        AS (
            SELECT
                *
            FROM {table_name}
        );
    """)
    
def save_to_temp_table(session, df: pd.DataFrame, table_name: str = "TEMP_TABLE") -> bool:
    """
    Save DataFrame to a temporary table in Snowflake. Create the table if it does not exist.
    """
    try:
        # Create the table if it does not exist
        # columns = ", ".join([f'"{col}" STRING' for col in df.columns])  # Assuming STRING as default data type
        # create_query = f"CREATE OR REPLACE TABLE {table_name} ({columns})"
        # session.sql(create_query).collect()
        # print(f"Temporary table {table_name} created successfully.")
        
        # # Replace NaN values with None
        # for column in df.columns:
        #     df[column] = df[column].where(pd.notna(df[column]), None)
        
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

# 3. In the filter_augment_table function:
def filter_augment_table(session, user_query):
    try:
        # Create search service with updated configurations
        create_cortex_search_service(session, "AUGMENT_TABLE")
        
        # Create search configuration with broader criteria
        search_config = {
            "query": user_query,
            "columns": [
                "CATEGORY_1", "CATEGORY_2", "CATEGORY_3", "DESCRIPTION",
                "HIGHLIGHTS", "IMAGE_LINKS", "MRP", "PRODUCT_ID", 
                "PRODUCT_RATING", "SELLER_NAME", "SELLER_RATING", "TITLE"
            ],
            "limit": 100  # Increased limit for more diverse results
        }
        
        
        search_json = json.dumps(search_config)
        query = build_search_query(search_json)
        
        # Execute search with error handling
        try:
            results = session.sql(query).to_pandas()
            if results.empty:
                raise ValueError("No search results found")
                
            parsed_results = results['SEARCH_RESULTS'].iloc[0]
            if isinstance(parsed_results, str):
                parsed_results = json.loads(parsed_results)
                
            if not isinstance(parsed_results, dict) or 'results' not in parsed_results:
                raise ValueError("Invalid results format")
                
            search_results = parsed_results['results']
            flattened_results = pd.json_normalize(search_results)
            
            if flattened_results.empty:
                raise ValueError("No results after flattening")
                
            # Process numeric columns and add randomization
            flattened_results = process_numeric_columns(flattened_results)

            if save_to_temp_table(session, flattened_results, "RECOMMENDATIONS_TABLE"):
                return flattened_results

        except Exception as search_error:
            print(f"Search error: {str(search_error)}")
            # Fallback to basic recommendations
            fallback_query = """
                SELECT * FROM PRODUCT_TABLE 
                WHERE TITLE IS NOT NULL 
                ORDER BY PRODUCT_RATING DESC, RANDOM() 
                LIMIT 20
            """
            return session.sql(fallback_query).to_pandas()
            
    except Exception as e:
        print(f"Error in filter_augment_table: {str(e)}")
        return pd.DataFrame()




# 2. In the perform_semantic_search function:
def perform_semantic_search(session, user_id, rank=100, threshold=0.3):
    try:
        # Create staging table with fresh data
        execute_query(session , """
            CREATE OR REPLACE TABLE product_table_stage AS 
            SELECT DISTINCT * 
            FROM temp_table 
            WHERE TITLE IS NOT NULL;
        """)
        
        # Generate embeddings for product titles
        execute_query(session ,"""
            ALTER TABLE product_table_stage 
            ADD COLUMN IF NOT EXISTS product_vec VECTOR(FLOAT, 768);
        """)
        
        execute_query(session ,"""
            UPDATE product_table_stage
            SET product_vec = SNOWFLAKE.CORTEX.EMBED_TEXT_768(
                'snowflake-arctic-embed-m', 
                COALESCE(TITLE, '')
            )
            WHERE product_vec IS NULL;
        """)
        
        # Generate embeddings for context
        execute_query(session ,"""
            ALTER TABLE context_table 
            ADD COLUMN IF NOT EXISTS context_vec VECTOR(FLOAT, 768);
        """)
        
        execute_query(session ,"""
            UPDATE context_table
            SET context_vec = SNOWFLAKE.CORTEX.EMBED_TEXT_768(
                'snowflake-arctic-embed-m', 
                COALESCE(TITLE, '')
            )
            WHERE context_vec IS NULL;
        """)
        
        # Perform semantic search with randomization for diversity
        execute_query(session ,f"""
            CREATE OR REPLACE TABLE augment_table AS
            WITH similarity_scores AS (
                SELECT 
                    p.*,
                    VECTOR_COSINE_SIMILARITY(c.context_vec, p.product_vec) AS similarity,
                    ROW_NUMBER() OVER (ORDER BY RANDOM()) as random_rank
                FROM context_table c
                CROSS JOIN product_table_stage p
                WHERE p.TITLE IS NOT NULL
            ),
            ranked_results AS (
                SELECT *
                FROM similarity_scores
                WHERE similarity > {threshold}
                ORDER BY similarity DESC, random_rank
                LIMIT {rank}
            )
            SELECT * FROM ranked_results
            ORDER BY similarity DESC, random_rank
            LIMIT {rank};
        """)
        
    except Exception as e:
        print(f"Error in semantic search: {str(e)}")
        # Fallback to basic recommendation
        execute_query(session ,f"""
            CREATE OR REPLACE TABLE augment_table AS
            SELECT *, 0.0 as similarity, ROW_NUMBER() OVER (ORDER BY PRODUCT_RATING DESC) as random_rank
            FROM product_table_stage
            LIMIT {rank};
        """)


def get_recommendations(session, human_query, user_id):

    cleanup_tables(session)
    
    human_query = human_query.replace('"', '').replace("'", "")

    mistral_query = get_mistral_query(session, human_query)
    st.write("mistral_query:",mistral_query)
    mistral_query = mistral_query.replace('"', '').replace("'", "")

    print(mistral_query)
    
    context = construct_context(session, user_id)
    print(f"Constructed Context: {context}")

    create_query = f"CREATE OR REPLACE TABLE TEMP_TABLE AS (SELECT * FROM PRODUCT_TABLE)"
    execute_query(session ,create_query)


    print("filter_temp_table\n")
    filter_temp_table(session, mistral_query)

    filter_context_table(session, mistral_query)
    
    print("perform_semantic_search\n")
    perform_semantic_search(session, user_id, rank=1000, threshold=0.0)
    try:
        return filter_augment_table(session, mistral_query)


    # try:
    #     # Query to fetch data from the specified table
    #     query = "SELECT * FROM RECOMMENDATIONS_TABLE;"
        
    #     # Execute the query and convert the result to a pandas DataFrame
    #     df = session.sql(query).to_pandas()
    #     st.write(df)
        
    #     print("Data successfully fetched from table RECOMMENDATIONS_TABLE.")
    #     print(df.head())  # Display the first few rows of the DataFrame
    #     return df
    except Exception as e:
        print(f"Error in get_recommendations: {str(e)}")
        # Return basic recommendations on error
        basic_query = "SELECT * FROM PRODUCT_TABLE ORDER BY RANDOM() LIMIT 6"
        return session.sql(basic_query).to_pandas()
    

# Snowflake connection parameters
# SNOWFLAKE_CONFIG = {
#     "account": "tjb57239",
#     "user": "HARSHA070804",
#     "password": "Harsha123",
#     "warehouse": "ECOMMERCE_WH",
#     "database": "ECOMMERCE_DB",
#     "schema": "PUBLIC"
# }

SNOWFLAKE_CONFIG = {
    "account": "xyb99777",
    "user": "TESTING",
    "password": "Harsha123",
    "warehouse": "ECOMMERCE_WH",
    "database": "ECOMMERCE_DB",
    "schema": "PUBLIC"
}

@st.cache_resource
def get_active_session():
    """Initialize and cache Snowflake connection"""
    try:
        conn = snowflake.connector.connect(
            account=SNOWFLAKE_CONFIG["account"],
            user=SNOWFLAKE_CONFIG["user"],
            password=SNOWFLAKE_CONFIG["password"],
            warehouse=SNOWFLAKE_CONFIG["warehouse"],
            database=SNOWFLAKE_CONFIG["database"],
            schema=SNOWFLAKE_CONFIG["schema"]
        )
        return conn
    except Exception as e:
        st.error(f"Failed to connect to Snowflake: {str(e)}")
        return None

def execute_query(session, query):
    """Execute a query and return results as a DataFrame"""
    try:
        cur = session.cursor()
        cur.execute(query)
        st.write("here in execute_query_1")
        
        # Get column names and results
        columns = [col[0] for col in cur.description]
        # results = cur.fetchall()
        session = Session.builder.configs(SNOWFLAKE_CONFIG).create()

        results = session.sql(query).collect()
        st.write(results)
        return pd.DataFrame(results, columns=columns)
    except Exception as e:
        st.error(f"Error executing query: {str(e)}")
        return pd.DataFrame()



@st.cache_data(ttl=0)  # Set TTL to 0 to disable caching
def fetch_recommendations(_session, human_query, user_id):
    # Clear any existing tables before running new query
    cleanup_tables(_session)
    return get_recommendations(_session, human_query, user_id)

# Initialize session states
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
            cur = session.cursor()
            cur.execute(query)
        except Exception as e:
            print(f"Error cleaning up table: {str(e)}")

def log_interaction(session, user_id, product_id, interaction_type):
    """Log user interactions with products"""
    if user_id:
        try:
            interaction_data = {
                'INTERACTION_TIMESTAMP': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'INTERACTION_TYPE': interaction_type,
                'PRODUCT_ID': product_id,
                'USER_ID': user_id
            }
            interaction_df = pd.DataFrame([interaction_data])
            # Convert to query and execute
            columns = ', '.join(interaction_data.keys())
            values = ', '.join([f"'{v}'" for v in interaction_data.values()])
            query = f"INSERT INTO USER_INTERACTIONS ({columns}) VALUES ({values})"
            cur = session.cursor()
            cur.execute(query)
            session.commit()
        except Exception as e:
            st.error(f"Error logging interaction: {str(e)}")

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

def display_product_card(product, col, session, idx):
    """Display a single product card"""
    with col:
        with st.container():
            st.markdown("""
                <style>
                    .product-card {
                        padding: 10px;
                        border: 1px solid #ddd;
                        border-radius: 10px;
                        margin: 10px 0;
                    }
                    .product-card:hover {
                        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    }
                </style>
            """, unsafe_allow_html=True)
            
            st.markdown('<div class="product-card">', unsafe_allow_html=True)
            
            # Display product image
            try:
                st.image(product['IMAGE_LINKS'], use_column_width=True)
            except:
                st.write("Image not available")
            
            # Display product information
            st.markdown(f"### {product['TITLE'][:50]}...")
            # st.write(f"⭐ Rating: {product['PRODUCT_RATING']}/5")
            # st.write(f"💰 Price: ₹{product['MRP']:,.2f}")
            
            # Action buttons
            cols = st.columns(2)
            with cols[0]:
                if st.button('View Details', key=f"view_{product['PRODUCT_ID']}_{idx}"):
                    st.session_state.current_product = product
                    st.session_state.page = 'detail'
                    if st.session_state.user_id:
                        log_interaction(session, st.session_state.user_id, 
                                     product['PRODUCT_ID'], 'view')
                    st.experimental_rerun()
            
            with cols[1]:
                if st.button('Add to Cart', key=f"cart_{product['PRODUCT_ID']}_{idx}"):
                    if product['PRODUCT_ID'] not in st.session_state.cart_items:
                        st.session_state.cart_items.append(product['PRODUCT_ID'])
                        if st.session_state.user_id:
                            log_interaction(session, st.session_state.user_id, 
                                         product['PRODUCT_ID'], 'add_to_cart')
                        st.success('Added to cart!')
            
            st.markdown('</div>', unsafe_allow_html=True)

def display_product_details(product, session):
    """Display detailed information about a product"""
    st.markdown("---")
    
    # Back button
    if st.button("← Back to Search Results"):
        st.session_state.page = 'home'
        st.session_state.current_product = None
        st.experimental_rerun()
    
    # Product title
    st.title(product['TITLE'])
    
    # Main product section
    col1, col2 = st.columns([1, 1])
    
    with col1:
        try:
            # st.markdown("""
            #     <style>
            #         .zoom-container {
            #             overflow: hidden;
            #             margin: 20px;
            #         }
            #         .zoom-container img {
            #             transition: transform .5s ease;
            #             cursor: zoom-in;
            #         }
            #         .zoom-container img:hover {
            #             transform: scale(1.5);
            #         }
            #     </style>
            # """, unsafe_allow_html=True)
            try:
                st.markdown("""
                    <style>
                        .zoom-container {
                            overflow: hidden;
                            margin: 20px;
                            width: 300px;  /* Fixed width */
                            height: 300px; /* Fixed height */
                        }
                        .zoom-container img {
                            width: 100%;  /* Ensures the image fits within the fixed container */
                            height: 100%; /* Ensures the image fits within the fixed container */
                            object-fit: cover;  /* Maintains aspect ratio within container */
                            transition: transform .5s ease;
                            cursor: zoom-in;
                        }
                        .zoom-container img:hover {
                            transform: scale(1.5);
                        }
                    </style>
                """, unsafe_allow_html=True)
                
                st.markdown('<div class="zoom-container">', unsafe_allow_html=True)
                st.image(product['IMAGE_LINKS'], width=300)  # Fixed width of 300 pixels
                st.markdown('</div>', unsafe_allow_html=True)
            except:
                st.write("Image not available")
            

            
            st.markdown('<div class="zoom-container">', unsafe_allow_html=True)
            st.image(product['IMAGE_LINKS'], use_column_width=100)
            st.markdown('</div>', unsafe_allow_html=True)
        except:
            st.write("Image not available")
    
    with col2:
        st.markdown("### Product Details")
        
        st.markdown("""
            <style>
                .info-box {
                    background-color: #f0f2f6;
                    padding: 20px;
                    border-radius: 10px;
                    margin: 10px 0;
                }
            </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="info-box">', unsafe_allow_html=True)
        st.write(f"**Category Path:**")
        st.write(f"{product['CATEGORY_1']} → {product['CATEGORY_2']} → {product['CATEGORY_3']}")
        
        # st.write(f"**Price:** ₹{product['MRP']:,.2f}")
        
        st.write(f"**Seller Information:**")
        st.write(f"Name: {product['SELLER_NAME']}")
        st.write(f"Rating: ⭐{product['SELLER_RATING']}/5")
        
        # st.write(f"**Product Rating:** ⭐{product['PRODUCT_RATING']}/5")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button('Add to Cart', key=f"detail_cart_{product['PRODUCT_ID']}", 
                        use_container_width=100):
                if product['PRODUCT_ID'] not in st.session_state.cart_items:
                    st.session_state.cart_items.append(product['PRODUCT_ID'])
                    if st.session_state.user_id:
                        log_interaction(session, st.session_state.user_id, 
                                     product['PRODUCT_ID'], 'add_to_cart')
                    st.success('Added to cart!')
        
        with col2:
            if st.button('Buy Now', key=f"buy_{product['PRODUCT_ID']}", 
                        use_container_width=100):
                if st.session_state.user_id:
                    log_interaction(session, st.session_state.user_id, 
                                  product['PRODUCT_ID'], 'purchase')
                st.success('Order placed successfully!')
    
    # Product information tabs
    st.markdown("### Product Information")
    tab1, tab2 = st.tabs(["Description", "Highlights"])
    
    with tab1:
        st.markdown(f"<div class='info-box'>{product['DESCRIPTION']}</div>", 
                   unsafe_allow_html=True)
    
    with tab2:
        try:
            highlights_list = json.loads(product['HIGHLIGHTS']) if product['HIGHLIGHTS'] else []
            for highlight in highlights_list:
                st.markdown(f"• {highlight}")
        except:
            st.write("No highlights available")


def main():
    st.set_page_config(page_title="Smart Shopping", layout="wide")
    
    session = get_active_session()
    
    # Display header section
    header_section()
    
    if st.session_state.page == 'home':
        st.markdown("## 🔍 Smart Product Search")
        
        # Search section with button
        col1, col2 = st.columns([4, 1])
        with col1:
            search_query = st.text_input(
                "",
                placeholder="E.g., 'suggest me a good comfortable badminton rackets for kids' or 'Suggest me aurvedic products for my gut problem'",
                key="search_input"
            )
        with col2:
            search_button = st.button("Search", use_container_width=True, key="search_button")
        
        # Initialize container for results
        results_container = st.container()
        
        # Only perform search when button is clicked
        if search_button and search_query:
            with st.spinner('Finding the perfect products for you...'):
                try:
                    suggestions_df = fetch_recommendations(session, search_query, 6)
                    
                    # Display results in the container
                    with results_container:
                        if not suggestions_df.empty:
                            st.success('Here are some products you might like!')
                            
                            # Display products in a grid
                            for i in range(0, len(suggestions_df), 2):
                                cols = st.columns(2)
                                if i < len(suggestions_df):
                                    display_product_card(suggestions_df.iloc[i], cols[0], session, f"search_{i}_left")
                                if i + 1 < len(suggestions_df):
                                    display_product_card(suggestions_df.iloc[i + 1], cols[1], session, f"search_{i}_right")
                        else:
                            st.info("No products found matching your search.")
                
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    st.error("Please try a different search query.")
        
        # Show trending products if no search has been performed
        elif not st.session_state.get('search_performed', False):
            with results_container:
                st.markdown("### 📈 Trending Products")
                try:
                    # Get trending products using cursor instead of sql method
                    default_query = """
                        SELECT * FROM PRODUCT_TABLE 
                        ORDER BY RANDOM() 
                        LIMIT 6
                    """
                    default_df = execute_query(session, default_query)
                    
                    if not default_df.empty:
                        for i in range(0, len(default_df), 2):
                            cols = st.columns(2)
                            if i < len(default_df):
                                display_product_card(default_df.iloc[i], cols[0], session, f"trend_{i}_left")
                            if i + 1 < len(default_df):
                                display_product_card(default_df.iloc[i + 1], cols[1], session, f"trend_{i}_right")
                    else:
                        st.info("No trending products available at the moment.")
                        
                except Exception as e:
                    st.error(f"Error loading trending products: {str(e)}")
    
    elif st.session_state.page == 'detail' and st.session_state.current_product is not None:
        display_product_details(st.session_state.current_product, session)

if __name__ == "__main__":
    main()
