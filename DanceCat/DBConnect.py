import mysql.connector
import pymssql
import traceback
import re
from DanceCat import Constants, Helpers


class DBConnect:
    def __init__(self, connection_type, config, **kwargs):
        self.type = connection_type
        self.config = config
        self.convert_sql = kwargs.get('convert_sql', False)
        self.no_password = kwargs.get('no_password', True)
        self.dict_format = kwargs.get('dict_format', False)
        self.timeout = kwargs.get('timeout', 30)

        self.connection = None
        self.cursor = None

        self.columns_name = ()
        self.ignore_position = []

    def connect(self):
        try:
            if self.type == Constants.MYSQL:
                self.config['connection_timeout'] = self.timeout
                self.connection = mysql.connector.connect(**self.config)
            elif self.type == Constants.SQLSERVER:
                self.connection = pymssql.connect(**self.config)
        except Exception:
            traceback.print_exc()
            raise DBConnectException('Could not connect to the database.', self.type)

    def close(self):
        try:
            if self.type in [
                Constants.MYSQL, Constants.SQLSERVER
            ]:
                self.connection.close()
        except Exception:
            traceback.print_exc()
            raise DBConnectException('Could not close the connection.', self.type)

    def connection_test(self):
        try:
            self.connect()
            self.close()
            return not not self.connection
        except DBConnectException:
            traceback.print_exc()
            return False

    def execute(self, query):
        try:
            if self.type == Constants.MYSQL:
                self.cursor = self.connection.cursor()
                self.cursor.execute(query)
                self.columns_name = self.cursor.column_names
                if self.no_password:
                    self.password_field_coordinator()

            elif self.type == Constants.SQLSERVER:
                self.cursor = self.connection.cursor()
                self.cursor.execute(query)

                # create columns' name tuple
                self.columns_name = ()
                for i in range(0, len(self.cursor.description)):
                    self.columns_name += (self.cursor.description[i][0],)
                if self.no_password:
                    self.password_field_coordinator()
        except mysql.connector.ProgrammingError as e:
            traceback.print_exc()
            raise DBConnectException('Could not query "%s"' % query, self.type, trace_back=e)
        except Exception:
            traceback.print_exc()
            raise DBConnectException('Could not query "%s".' % query, self.type)
        else:
            return True

    def fetch(self):
        try:
            if self.type in [Constants.MYSQL, Constants.SQLSERVER]:
                data = self.cursor.fetchone()
                return self.convert_dict_one(data) if self.dict_format else self.tuple_process_one(data)
        except Exception:
            traceback.print_exc()
            raise DBConnectException('Could not fetch result(s).', self.type)

    def fetch_many(self, size=1):
        try:
            if self.type in [Constants.MYSQL, Constants.SQLSERVER]:
                data = self.cursor.fetchmany(size)
                return self.convert_dict_many(data) if self.dict_format else self.tuple_process_many(data)
        except Exception:
            traceback.print_exc()
            raise DBConnectException('Could not fetch result(s).', self.type)

    def fetch_all(self):
        try:
            if self.type in [Constants.MYSQL, Constants.SQLSERVER]:
                data = self.cursor.fetchall()
                return self.convert_dict_many(data) if self.dict_format else self.tuple_process_many(data)
        except Exception:
            traceback.print_exc()
            raise DBConnectException('Could not fetch result(s).', self.type)

    def convert_dict_one(self, data_tuple):
        if len(self.columns_name) == 0:
            raise DBConnectException('Column(s) name is empty.', self.type)

        data_dict = {}

        for i in range(0, len(self.columns_name)):
            if i in self.ignore_position:
                continue
            data_dict[self.columns_name[i]] = \
                Helpers.py2sql_type_convert(data_tuple[i]) if self.convert_sql else data_tuple[i]

        return data_dict

    def convert_dict_many(self, data_tuple_list):
        if len(self.columns_name) == 0:
            raise DBConnectException('Column(s) name is empty.', self.type)

        data_dict_list = []

        for i in range(0, len(data_tuple_list)):
            data_dict = {}

            for j in range(0, len(self.columns_name)):
                if j in self.ignore_position:
                    continue
                data_dict[self.columns_name[j]] = \
                    Helpers.py2sql_type_convert(data_tuple_list[i][j]) if self.convert_sql else data_tuple_list[i][j]

            data_dict_list.append(data_dict)

        return data_dict_list

    def tuple_process_one(self, data_tuple):
        new_data_tuple = ()

        for i in range(0, len(data_tuple)):
            if i in self.ignore_position:
                continue
            new_data_tuple += (Helpers.py2sql_type_convert(data_tuple[i]) if self.convert_sql else data_tuple[i],)

        return new_data_tuple

    def tuple_process_many(self, data_tuple_list):
        new_data_tuple_list = []

        for i in range(0, len(data_tuple_list)):
            new_data_tuple_list.append(self.tuple_process_one(data_tuple_list[i]))

        return new_data_tuple_list

    def password_field_coordinator(self):
        if len(self.columns_name) == 0:
            raise DBConnectException('Column(s) name is empty.', self.type)
        for i in range(0, len(self.columns_name)):
            if self.no_password:
                if re.search(r'password|secret', self.columns_name[i], re.IGNORECASE) is not None:
                    self.ignore_position.append(i)


class DBConnectException(Exception):
    def __init__(self, message, connection_type, trace_back=None):
        super(DBConnectException, self).__init__(message)

        self.connection_type = connection_type
        self.trace_back = trace_back
