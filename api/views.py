from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import QuerySerializer
from datetime import datetime
from django.db import connection, DatabaseError
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class ProcessPromptView(APIView):
    """
    API endpoint that receives an SQL query and returns a response after executing
    the query on the production PostgreSQL database.
    """
    
    authentication_classes = []  # Disables all authentication for this view
    
    @swagger_auto_schema(
        operation_id="processPrompt",
        operation_summary="Send an SQL query to the database and return a response.",
        operation_description=(
            "Sends an SQL query generated based on the user's question and provided database schema "
            "information from a connected production database."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['query'],
            properties={
                'query': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="The SQL query to be processed."
                )
            },
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "response": openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "success": openapi.Schema(
                                type=openapi.TYPE_BOOLEAN,
                                description="Whether the query was successful."
                            ),
                            "data": openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        "count": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="The count of records retrieved."
                                        )
                                    }
                                )
                            )
                        }
                    ),
                    "last_Update_Time": openapi.Schema(
                        type=openapi.FORMAT_DATETIME,
                        description="The last time the data was updated on customer call details."
                    )
                }
            ),
            400: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "error": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="Invalid request. Ensure the query was provided."
                    )
                }
            ),
            401: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "error": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="Unauthorized. Invalid or missing userId."
                    )
                }
            ),
            500: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "error": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="Internal server error. An error occurred while processing the request."
                    )
                }
            )
        }
    )
    def post(self, request):
        # Check for user authentication via the userId header.
        # user_id = request.headers.get("userId")
        # if not user_id:
        #     return Response(
        #         {"error": "Unauthorized. Invalid or missing userId."},
        #         status=status.HTTP_401_UNAUTHORIZED
        #     )

        serializer = QuerySerializer(data=request.data)
        if serializer.is_valid():
            sql_query = serializer.validated_data['query']

            try:
                # Execute the SQL query using Django's database connection.
                with connection.cursor() as cursor:
                    cursor.execute(sql_query)
                    # If the query returns rows (e.g., a SELECT statement)
                    if cursor.description:
                        columns = [col[0] for col in cursor.description]
                        rows = cursor.fetchall()
                        # Convert the rows into a list of dictionaries
                        result = [dict(zip(columns, row)) for row in rows]
                    else:
                        # For non-SELECT queries (INSERT, UPDATE, DELETE), there is no result set.
                        result = []

                last_update_time = datetime.utcnow().isoformat() + "Z"
                response_data = {
                    "response": {
                        "success": True,
                        "data": result
                    },
                    "last_Update_Time": last_update_time
                }
                return Response(response_data, status=status.HTTP_200_OK)
            except DatabaseError:
                # Log the exception as needed for debugging.
                return Response(
                    {"error": "Internal server error while processing the query."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TableSchemaView(APIView):
    """
    API endpoint that retrieves the schema for specified PostgreSQL tables.
    """
    
    @swagger_auto_schema(
        operation_id="getTableSchema",
        operation_summary="Retrieve schema for specified tables",
        operation_description=(
            "Retrieves column information for the specified tables in a PostgreSQL database. "
            "Accepts a comma-separated list of table names."
        ),
        manual_parameters=[
            openapi.Parameter(
                name='tables',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Comma-separated list of table names",
                required=True
            )
        ],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "schemas": openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        description="Schema information for each requested table"
                    )
                }
            ),
            400: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "error": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="Error message for invalid request"
                    )
                }
            ),
            500: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "error": openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="Internal server error"
                    )
                }
            )
        }
    )
    def get(self, request):
        # Get the comma-separated list of table names from query parameters
        tables_param = request.query_params.get('tables', '')
        
        # Validate input
        if not tables_param:
            return Response(
                {"error": "No tables specified. Please provide a comma-separated list of table names."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Split the input and clean up table names
        tables = [table.strip() for table in tables_param.split(',') if table.strip()]
        
        if not tables:
            return Response(
                {"error": "Invalid table names provided."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Dictionary to store schema information for each table
            table_schemas = {}
            
            with connection.cursor() as cursor:
                for table_name in tables:
                    # PostgreSQL-specific query to get column information
                    cursor.execute("""
                        SELECT 
                            column_name, 
                            data_type, 
                            is_nullable, 
                            column_default
                        FROM 
                            information_schema.columns
                        WHERE 
                            table_name = %s
                    """, [table_name])
                    
                    # Fetch column details
                    columns = cursor.fetchall()
                    
                    # If no columns found, it might mean the table doesn't exist
                    if not columns:
                        table_schemas[table_name] = {"error": "Table not found"}
                        continue
                    
                    # Prepare column schema information
                    column_details = [
                        {
                            "name": col[0],
                            "type": col[1],
                            "nullable": col[2] == 'YES',
                            "default": col[3]
                        } for col in columns
                    ]
                    
                    table_schemas[table_name] = column_details
            
            return Response({"schemas": table_schemas}, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Log the exception for debugging
            return Response(
                {"error": f"An error occurred while retrieving table schemas: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )