# MindMart Smart Shopping 🛍️

MindMart is an intelligent e-commerce platform that combines semantic search, personalized recommendations, and user interaction tracking to provide a smart shopping experience. Built with Streamlit and Snowflake, it uses advanced NLP models for better product discovery and personalization.

## Features ✨

- **Smart Search**: Uses Mistral LLM and semantic search to understand user intent and find relevant products
- **Personalized Recommendations**: Leverages user interaction history to provide tailored product suggestions
- **User Authentication**: Secure login and registration system
- **Interactive UI**: Clean and intuitive interface with product cards and detailed views
- **Real-time Interaction Tracking**: Monitors user activities like views, likes, cart additions, and purchases
- **Vector Embeddings**: Utilizes Snowflake's vector search capabilities for semantic similarity matching

## Technology Stack 🛠️

- **Frontend**: Streamlit
- **Backend & Database**: Snowflake
- **Vector Search**: Snowflake Cortex Search Service
- **Language Models**: 
  - Mistral LLM for query understanding
  - Snowflake Arctic Embedding Models
- **Authentication**: Custom implementation with password hashing
- **Data Processing**: Pandas for data manipulation

## Prerequisites 📋

- Python 3.7+
- Snowflake account with appropriate permissions
- The following Python packages:
  ```
  streamlit
  snowflake-connector-python
  snowflake-snowpark-python
  pandas
  ```

## Installation 🔧

1. Clone the repository:
   ```bash
   git clone https://github.com/harshavardhan784/RAG-n-ROLL.git
   cd RAG-n-ROLL
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure Snowflake credentials:
   - Update the `SNOWFLAKE_CONFIG` dictionary in the code with your credentials:
     ```python
     SNOWFLAKE_CONFIG = {
         "account": "your-account",
         "user": "your-username",
         "password": "your-password",
         "warehouse": "your-warehouse",
         "database": "your-database",
         "schema": "your-schema"
     }
     ```

## Database Setup 🗄️

Ensure the following tables are created in your Snowflake database:

1. USER_TABLE
2. PRODUCT_TABLE
3. USER_INTERACTION_TABLE
4. Required temporary tables will be created automatically during runtime

## Running the Application 🚀

1. Start the Streamlit application:
   ```bash
   streamlit run app.py
   ```

2. Access the application through your web browser at `http://localhost:8501`

## Application Structure 🏗️

- **Authentication System**: Handles user registration and login
- **Product Search**: Processes natural language queries into semantic search
- **Recommendation Engine**: Combines user history and product similarity
- **Interaction Tracking**: Monitors and logs user activities
- **Product Display**: Shows products in cards with interaction buttons
- **Detail View**: Provides comprehensive product information

## Features in Detail 🔍

### Smart Search
- Converts natural language queries to semantic search queries using Mistral LLM
- Uses vector embeddings for similarity matching
- Combines user context with search results

### User Interactions
- Like products
- Add to cart
- View details
- Purchase products
- All interactions are logged for personalization

### Product Recommendations
- Based on user interaction history
- Semantic similarity matching
- Random recommendations for new users

## Security 🔒

- Passwords are hashed using SHA-256
- Secure session management
- Protected database credentials

## Contributing 🤝

1. Fork the repository
2. Create a new branch (`git checkout -b feature/improvement`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/improvement`)
5. Create a Pull Request


## Future development roadmap
1. Enhanced Search Capabilities
   - Image-based search functionality
   - Voice command integration
   - Social media content analysis (Instagram posts and Reels)
2. Advanced Recommendation System
   - Implementation of deep learning algorithms
   - Enhanced personalization features
   - Improved context awareness

## License 📄

This project is licensed under the MIT License - see the LICENSE file for details.


## Acknowledgments 🙏

- Snowflake for providing the database and vector search capabilities
- Streamlit for the web framework
- Mistral LLM for natural language understanding
- All contributors and users of the platform

## Support 💬

For support, please open an issue in the GitHub repository or contact the maintainers.

---

Built with ❤️ for smart shopping experiences
