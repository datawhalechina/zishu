"""
SQL 代码执行器
使用 SQLite 内存数据库执行 SQL 查询
"""
import sqlite3
from typing import Dict, Any, List, Tuple


class SQLExecutor:
    """SQL 代码执行器（使用 SQLite 内存数据库）"""

    # 示例数据初始化 SQL
    SAMPLE_DATA = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        age INTEGER,
        city TEXT,
        email TEXT
    );

    INSERT INTO users VALUES (1, '张三', 25, '北京', 'zhangsan@example.com');
    INSERT INTO users VALUES (2, '李四', 30, '上海', 'lisi@example.com');
    INSERT INTO users VALUES (3, '王五', 28, '深圳', 'wangwu@example.com');
    INSERT INTO users VALUES (4, '赵六', 35, '广州', 'zhaoliu@example.com');
    INSERT INTO users VALUES (5, '钱七', 22, '杭州', 'qianqi@example.com');
    INSERT INTO users VALUES (6, '孙八', 27, '成都', 'sunba@example.com');
    INSERT INTO users VALUES (7, '周九', 32, '南京', 'zhoujiu@example.com');
    INSERT INTO users VALUES (8, '吴十', 29, '武汉', 'wushi@example.com');

    CREATE TABLE orders (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        product TEXT,
        amount REAL,
        order_date TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    INSERT INTO orders VALUES (1, 1, '笔记本电脑', 5999.00, '2024-01-15');
    INSERT INTO orders VALUES (2, 2, '手机', 3999.00, '2024-01-16');
    INSERT INTO orders VALUES (3, 1, '鼠标', 99.00, '2024-01-17');
    INSERT INTO orders VALUES (4, 3, '键盘', 299.00, '2024-01-18');
    INSERT INTO orders VALUES (5, 4, '显示器', 1999.00, '2024-01-19');
    INSERT INTO orders VALUES (6, 2, '耳机', 599.00, '2024-01-20');
    INSERT INTO orders VALUES (7, 5, '平板', 2999.00, '2024-01-21');
    INSERT INTO orders VALUES (8, 3, '充电宝', 99.00, '2024-01-22');
    INSERT INTO orders VALUES (9, 6, '蓝牙音箱', 299.00, '2024-01-23');
    INSERT INTO orders VALUES (10, 7, '智能手表', 1999.00, '2024-01-24');

    CREATE TABLE products (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT,
        price REAL,
        stock INTEGER
    );

    INSERT INTO products VALUES (1, '笔记本电脑', '电子产品', 5999.00, 50);
    INSERT INTO products VALUES (2, '手机', '电子产品', 3999.00, 100);
    INSERT INTO products VALUES (3, '鼠标', '电子产品', 99.00, 200);
    INSERT INTO products VALUES (4, '键盘', '电子产品', 299.00, 150);
    INSERT INTO products VALUES (5, '显示器', '电子产品', 1999.00, 80);
    INSERT INTO products VALUES (6, '耳机', '电子产品', 599.00, 120);
    INSERT INTO products VALUES (7, '平板', '电子产品', 2999.00, 60);
    INSERT INTO products VALUES (8, '充电宝', '电子产品', 99.00, 300);
    INSERT INTO products VALUES (9, '蓝牙音箱', '电子产品', 299.00, 90);
    INSERT INTO products VALUES (10, '智能手表', '电子产品', 1999.00, 70);
    """

    # 禁止的危险 SQL 命令
    FORBIDDEN_COMMANDS = [
        'PRAGMA',      # 可能修改数据库设置
        'ATTACH',      # 可能附加外部数据库
        'DETACH',      # 分离数据库
        'LOAD',        # 加载扩展
        'SAVEPOINT',   # 保存点（可能用于绕过限制）
    ]

    def _is_safe_sql(self, sql: str) -> tuple[bool, str]:
        """
        检查 SQL 是否安全

        Returns:
            (is_safe, error_message)
        """
        sql_upper = sql.strip().upper()

        for forbidden in self.FORBIDDEN_COMMANDS:
            if forbidden in sql_upper:
                return False, f'禁止使用 {forbidden} 命令'

        return True, ''

    async def execute(self, sql: str) -> Dict[str, Any]:
        """
        在 SQLite 内存数据库中执行 SQL

        Args:
            sql: SQL 查询语句

        Returns:
            dict: { success, stdout, stderr, exitCode, rowCount }
        """
        # 安全检查
        is_safe, error_msg = self._is_safe_sql(sql)
        if not is_safe:
            return {
                'success': False,
                'stdout': '',
                'stderr': error_msg,
                'exitCode': 1
            }

        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()

        try:
            # 初始化示例数据
            cursor.executescript(self.SAMPLE_DATA)
            conn.commit()

            # 检测 SQL 类型
            sql_upper = sql.strip().upper()

            if sql_upper.startswith('SELECT') or sql_upper.startswith('WITH'):
                # 查询语句 - 返回数据
                cursor.execute(sql)
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()

                # 限制返回行数
                result_rows = rows[:1000]

                # 格式化表格输出
                table_output = self._format_table(columns, result_rows)

                return {
                    'success': True,
                    'stdout': table_output,
                    'stderr': '',
                    'exitCode': 0,
                    'rowCount': len(result_rows)
                }
            else:
                # 非查询语句 (INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, etc.)
                cursor.execute(sql)
                conn.commit()

                return {
                    'success': True,
                    'stdout': f'执行成功，影响 {cursor.rowcount} 行',
                    'stderr': '',
                    'exitCode': 0,
                    'rowCount': cursor.rowcount
                }

        except sqlite3.Error as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': f'SQL 错误: {str(e)}',
                'exitCode': 1
            }
        finally:
            conn.close()

    def _format_table(self, columns: List[str], rows: List[Tuple]) -> str:
        """格式化表格输出为文本"""
        if not rows:
            return '空结果集'

        # 计算每列的最大宽度
        col_widths = [len(str(col)) for col in columns]
        for row in rows:
            for i, val in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(val)))

        # 构建分隔线
        separator = '+' + '+'.join('-' * (w + 2) for w in col_widths) + '+'

        # 构建表头
        header = '|' + '|'.join(f' {str(col).ljust(col_widths[i])} ' for i, col in enumerate(columns)) + '|'

        # 构建数据行
        data_rows = []
        for row in rows:
            data_row = '|' + '|'.join(f' {str(val).ljust(col_widths[i])} ' for i, val in enumerate(row)) + '|'
            data_rows.append(data_row)

        # 限制显示行数（最多100行）
        display_rows = data_rows[:100]
        if len(data_rows) > 100:
            display_rows.append(f'... (还有 {len(data_rows) - 100} 行未显示)')

        return '\n'.join([separator, header, separator] + display_rows + [separator])
