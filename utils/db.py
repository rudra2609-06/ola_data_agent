import os

import psycopg2

from typing import Optional


class DatabaseUtil:

    def __init__(self, db_config=None):
        """Initializes the DatabaseUtil class with the provided database configuration."""
        url = os.environ.get("POSTGRES_DB_URL")        
        try:
            self.connection = psycopg2.connect(url)
        except psycopg2.Error as e:
            print(f"Error connecting to the database: {e}")
            self.connection = None

    def collect_context(self, schema_name="public", table_name=Optional[str]) -> str:
        """The aim of this method is to collect the context of the database connection, such as table names, column names, and data types. This information can be useful for understanding the structure of the database as context for further operations while working with sql analyst agent."""
        cursor = None
        try:
            schema_info_context = f"Schema: {schema_name}\n"
            conn = self.connection
            cursor = conn.cursor()

            # Fetching all table names for the context
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = %s;",
                (schema_name,),
            )
            tables_list = cursor.fetchall()

            if table_name is not None:
                tables_list = [table for table in tables_list if table[0].lower() == table_name ]

            for table in tables_list:
                table_name = table[0]

                # Adding individual tables to the context
                schema_info_context += f"Table: {table_name}\n"

                cursor.execute(
                    "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = %s AND table_name = %s;",
                    (schema_name, table_name),
                )
                column_list = cursor.fetchall()

                for column in column_list:
                    column_name, data_type = column

                    # Adding individual columns and data types to the context
                    schema_info_context += (
                        f"  Column: {column_name}, Data Type: {data_type}\n"
                    )

                # Adding sample data for each table to the context
                cursor.execute(f"SELECT * FROM {schema_name}.{table_name} LIMIT 5;")
                sample_data = cursor.fetchall()

                for row in sample_data:
                    schema_info_context += f"    {row}\n"

            return schema_info_context

        except Exception as e:
            print(f"Error while collecting context: {e}")
            raise

    def execute_query(self, query) -> str:
        """
        Helper fn that helps in executing sql queries
        and returns the results in string format
        """
        try:
            conn = self.connection
            cursor = conn.cursor()
            cursor.execute(query)
            res = cursor.fetchall()
            conn.commit()
            return str(res)
        except Exception as e:
            print(f"Executing Generated SQL Query failed due to {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()


if __name__ == "__main__":
    obj = DatabaseUtil(
        {
            "host": "localhost",
            "port": 5432,
            "dbname": "postgres",
            "user": "postgres",
            "password": os.getenv("POSTGRES_PASSWORD"),
        }
    )
    res = obj.collect_context("public")
    print(res)
