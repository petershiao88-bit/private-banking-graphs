const statement=query.replace(/--[^\r\n]*/g,'').replace(/\/\*[\s\S]*?\*\//g,'').replace(/'(?:''|[^'])*'/g,"''").trim();
if(!/^(SELECT|WITH)\b/i.test(statement) || /\b(INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|TRUNCATE|MERGE|COPY|CALL|DO|GRANT|REVOKE|INTO)\b/i.test(statement) || statement.replace(/;\s*$/,'').includes(';')) return "SELECT 'KB_SQL_NOT_READ_ONLY' AS error_message;";
