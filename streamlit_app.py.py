import streamlit as st
import snowflake.connector
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="Snowflake Data Explorer",
    layout="wide"
)

# Snowflake connection parameters
SNOWFLAKE_CONFIG = {
    "account": "tjb57239",
    "user": "HARSHA070804",
    "password": "Harsha123",
    "warehouse": "ECOMMERCE_WH",
    "database": "ECOMMERCE_DB",
    "schema": "PUBLIC"
}

@st.cache_resource
def init_snowflake_connection():
    """Initialize Snowflake connection with caching."""
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

def fetch_data(conn, table_name, search_term=""):
    """Fetch data from specified table."""
    try:
        if search_term:
            query = f"""
            SELECT *
            FROM {table_name}
            WHERE LOWER(CONCAT(name, ' ', email)) LIKE LOWER('%{search_term}%')
            LIMIT 5
            """
        else:
            query = f"""
            SELECT *
            FROM {table_name}
            LIMIT 5
            """
        
        cur = conn.cursor()
        cur.execute(query)
        
        # Get column names and results
        columns = [col[0] for col in cur.description]
        results = cur.fetchall()
        
        return pd.DataFrame(results, columns=columns)
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return pd.DataFrame()

def main():
    st.title("🔍 Snowflake Data Explorer")
    
    # Initialize connection
    conn = init_snowflake_connection()
    
    if conn:
        st.success("✅ Connected to Snowflake successfully!")
        
        # Search section
        st.subheader("🔎 Search Data")
        table_name = st.text_input("Enter table name:", "YOUR_TABLE_NAME")
        search_term = st.text_input("Enter search term:")
        
        if st.button("Search"):
            with st.spinner("Fetching data..."):
                df = fetch_data(conn, table_name, search_term)
                if not df.empty:
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No results found.")
        
        # Add a section for raw SQL queries
        st.subheader("📝 Custom SQL Query")
        user_query = st.text_area("Enter your SQL query:", height=100)
        if st.button("Execute Query"):
            try:
                cur = conn.cursor()
                cur.execute(user_query)
                results = cur.fetchall()
                columns = [col[0] for col in cur.description]
                df = pd.DataFrame(results, columns=columns)
                st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"Query execution failed: {str(e)}")

if __name__ == "__main__":
    main()