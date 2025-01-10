import streamlit as st
import snowflake.connector

# Snowflake connection parameters
SNOWFLAKE_CONFIG = {
    "account": "tjb57239",  # Account identifier
    "user": "HARSHA070804",  # Your Snowflake username
    "password": "Harsha123",  # Your Snowflake password
    "warehouse": "ECOMMERCE_WH",  # Warehouse name
    "database": "ECOMMERCE_DB",  # Database name
    "schema": "PUBLIC"  # Schema name
}

def init_snowflake_connection(config):
    """Initialize Snowflake connection."""
    try:
        conn = snowflake.connector.connect(
            account=config["account"],
            user=config["user"],
            password=config["password"],
            warehouse=config["warehouse"],
            database=config["database"],
            schema=config["schema"],
        )
        return conn
    except Exception as e:
        st.error(f"Failed to connect to Snowflake: {str(e)}")
        return None

def create_table(conn):
    """Create a table in Snowflake."""
    try:
        query = """
        CREATE TABLE IF NOT EXISTS demo_table (
            id INT AUTOINCREMENT PRIMARY KEY,
            name STRING,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cur = conn.cursor()
        cur.execute(query)
        conn.commit()
        st.success("Table 'demo_table' created successfully!")
    except Exception as e:
        st.error(f"Failed to create table: {str(e)}")

def main():
    st.title("Snowflake Table Creator")

    # Connect to Snowflake
    conn = init_snowflake_connection(SNOWFLAKE_CONFIG)
    if conn:
        st.text("here")  # Debugging message for Streamlit
        st.success("Connected to Snowflake successfully!")

        # Button to create a table
        if st.button("Create Table"):
            create_table(conn)

        # Close connection when done
        conn.close()

if __name__ == "__main__":
    main()
