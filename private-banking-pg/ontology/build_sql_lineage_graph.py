"""Preserve source SQL and build direct table links with SQL rule properties.

Only parse SQL; never execute it against Oracle. Install the pinned parser in
.scratch/sql-lineage-runtime, or use an environment with sqlglot 27.29.0.
"""
from __future__ import annotations
from collections import Counter, defaultdict, deque
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.scratch/sql-lineage-runtime'))
import sqlglot
from sqlglot import exp

NS = 'sql_lineage'
OWNER = 'sql_lineage_v1'
FILES = [
    ('1.AUM_DETAIL.sql', 'aum', 'primary_reference'),
    ('2._AUM_SUMY.sql', 'aum', 'primary_reference'),
    ('8.INCOME_DETAIL.sql', 'income', 'primary_reference'),
    ('9.INCOME_SMY.sql', 'income', 'primary_reference'),
    ('X-INCOME_MOTHLY.sql', 'income', 'auxiliary_monthly_reference'),
    ('10._INCOME_ROA.sql', 'shared', 'primary_reference'),
    # AUM_TMP02 is referenced by ROA but defined only in this alternate file.
    ('2._AUM_SUMY.~sql', 'aum', 'alternate_file_reference'),
]
TOKENS = re.compile(r"'(?:(?:'')|[^'])*'|\"(?:\"\"|[^\"])*\"|/\*[\s\S]*?\*/|--[^\n]*")


def blank_comments(text):
    return TOKENS.sub(lambda m: re.sub(r'[^\n]', ' ', m[0])
                      if m[0].startswith(('/*', '--')) else m[0], text)


def parser_text(text):
    # Preserve exact source separately. Oracle DB links are omitted ONLY from
    # parser input, with the normalization and links recorded on statements.
    return TOKENS.sub(lambda m: m[0], text) if '@' not in text else re.sub(
        r"'(?:(?:'')|[^'])*'|@[A-Za-z0-9_.$]+",
        lambda m: m[0] if m[0].startswith("'") else '', text)


def sql(expr):
    return expr.sql(dialect='oracle') if expr is not None else ''


def statements(text):
    """Return DDL/DML blocks, including definitions inside block comments."""
    surfaces = [(blank_comments(text), 'active_sql')]
    for m in TOKENS.finditer(text):
        if m[0].startswith('/*') and re.search(r'\bcreate\s+table\b', m[0], re.I):
            inner = m[0][2:-2]
            # Retain line numbers before the commented region.
            surface = re.sub(r'[^\n]', ' ', text[:m.start()+2]) + blank_comments(inner)
            surfaces.append((surface, 'commented_out_sql'))
    result = []
    for surface, status in surfaces:
        # A semicolon in a quoted literal cannot terminate a SQL statement.
        masked = TOKENS.sub(lambda m: re.sub(r'[^\n]', ' ', m[0]), surface)
        for m in re.finditer(r'\b(?:CREATE\s+TABLE|INSERT\s+INTO|DELETE\s+FROM|TRUNCATE\s+TABLE|UPDATE)\s+[\w.$]+', masked, re.I):
            end = masked.find(';', m.start())
            if end < 0:
                raise ValueError(f'Unterminated SQL at offset {m.start()}')
            result.append({'start': m.start(), 'end': end+1, 'status': status,
                           'parserSql': surface[m.start():end+1],
                           'sql': text[m.start():end+1]})
    return sorted(result, key=lambda r: r['start'])


class Graph:
    def __init__(self):
        self.nodes = {}
        self.edges = {}
        self.records = []
        self.table_domains = defaultdict(set)
        self.table_definitions = defaultdict(list)
        self.root = self.node('SqlLineageRoot', f'{NS}:root', name='AUM／Income 原始 SQL 血緣',
                              parserVersion=sqlglot.__version__, dialect='oracle')

    def node(self, label, key, **props):
        props = {k: v for k, v in props.items() if v is not None}
        props.update(ontologyId=NS, origin=OWNER)
        if key in self.nodes:
            assert self.nodes[key]['label'] == label
            self.nodes[key]['properties'].update(props)
        else:
            self.nodes[key] = {'label': label, 'key': key, 'properties': props}
        return key

    def edge(self, source, kind, target, **props):
        props.update(ontologyId=NS, origin=OWNER)
        identity = json.dumps([source, kind, target, props], sort_keys=True, ensure_ascii=False)
        edge_id = hashlib.sha256(identity.encode()).hexdigest()
        self.edges[edge_id] = {'from': source, 'to': target, 'type': kind,
                              'properties': dict(props, lineageEdgeId=edge_id)}

    def table(self, name, domain):
        name = name.upper()
        key = self.node('SqlTable', f'{NS}:table:{name}', name=name, physicalName=name)
        self.table_domains[key].add(domain)
        return key

    def validate(self):
        assert all(e['from'] in self.nodes and e['to'] in self.nodes for e in self.edges.values())
        adjacency = defaultdict(set)
        for e in self.edges.values():
            adjacency[e['from']].add(e['to']); adjacency[e['to']].add(e['from'])
        seen = {self.root}; queue = deque([self.root])
        while queue:
            for n in adjacency[queue.popleft()]-seen:
                seen.add(n); queue.append(n)
        assert len(seen) == len(self.nodes), (len(seen), len(self.nodes))


class StatementBuilder:
    def __init__(self, graph, record):
        self.g = graph
        self.record = record
        self.counter = 0
        self.ctes = {}
        self.read_tables = set()

    def operation(self, kind, expression, **props):
        self.counter += 1
        suffix = '（註解）' if self.record['status'] == 'commented_out_sql' else '（備份版本）' if self.record['sourceRole'] == 'alternate_file_reference' else ''
        names = {'SELECT': 'SELECT 欄位映射', 'FILTER': 'WHERE 篩選',
                 'AGGREGATE': 'GROUP BY／彙總', 'CASE': 'CASE 分類',
                 'UNION': 'UNION 去除完全相同列', 'UNION ALL': 'UNION ALL 保留重複列',
                 'DISTINCT': 'DISTINCT 去重', 'HAVING': 'HAVING 篩選',
                 'ORDER BY': 'ORDER BY', 'LIMIT': '列數限制'}
        captions = {'SELECT':'SELECT', 'FILTER':'WHERE', 'AGGREGATE':'GROUP BY',
                    'CASE':'CASE', 'CREATE TABLE AS':'CREATE 表',
                    'UNION':'UNION', 'UNION ALL':'UNION ALL'}
        key = self.g.node('SqlOperation', f"{self.record['key']}:op:{self.counter:03}",
                          name=captions.get(kind,kind)+suffix, description=names.get(kind,kind), operationType=kind,
                          domain=self.record['domain'], statementKey=self.record['key'],
                          outputTable=self.record['output'], file=self.record['file'],
                          lineStart=self.record['lineStart'], lineEnd=self.record['lineEnd'],
                          status=self.record['status'], sourceRole=self.record['sourceRole'],
                          sql=sql(expression), sqlTextKind='parser_reconstructed_fragment',
                          **props)
        self.g.edge(self.record['key'], 'HAS_OPERATION', key)
        return key

    def input(self, source, target, index=1, kind='FLOWS_TO', **props):
        self.g.edge(source, kind, target, inputOrder=index, **props)

    def query(self, expr):
        if isinstance(expr, (exp.Subquery, exp.Paren)):
            return self.query(expr.this)
        if isinstance(expr, exp.Table):
            name = '.'.join(p.name for p in expr.parts).upper()
            if name in self.ctes:
                return self.ctes[name]
            key = self.g.table(name,self.record['domain'])
            self.read_tables.add(key)
            return key
        with_expr = expr.args.get('with')
        if with_expr:
            for cte in with_expr.expressions:
                self.ctes[cte.alias_or_name.upper()] = self.query(cte.this)
        if isinstance(expr, exp.SetOperation):
            distinct = bool(expr.args.get('distinct', True))
            kind = 'UNION' if isinstance(expr,exp.Union) and distinct else 'UNION ALL' if isinstance(expr,exp.Union) else expr.key.upper()
            leaves = []
            def flatten(e):
                if type(e) is type(expr) and bool(e.args.get('distinct', True)) == distinct:
                    flatten(e.this); flatten(e.expression)
                else:
                    leaves.append(e)
            flatten(expr)
            inputs = [self.query(e) for e in leaves]
            op = self.operation(kind,expr,branchCount=len(inputs),
                                deduplication='exact_projected_rows' if distinct else 'none',
                                branchSql=[sql(e) for e in leaves])
            for i, inp in enumerate(inputs,1): self.input(inp,op,i,kind='UNION_INPUT')
            return op
        if not isinstance(expr, exp.Select):
            raise ValueError(f'Unsupported query node: {type(expr).__name__}: {sql(expr)}')
        from_expr = expr.args.get('from')
        current = self.query(from_expr.this) if from_expr else None
        for join in expr.args.get('joins',[]):
            right = self.query(join.this)
            side = str(join.args.get('side') or '').upper()
            jkind = str(join.args.get('kind') or '').upper()
            kind = ' '.join(x for x in [side,jkind,'JOIN'] if x)
            if kind == 'JOIN' and not join.args.get('on') and not join.args.get('using'):
                kind = 'CROSS JOIN'
            op = self.operation(kind,join,joinType=kind,
                                condition=sql(join.args.get('on')),
                                usingColumns=[sql(x) for x in join.args.get('using',[])],
                                leftAlias=from_expr.this.alias_or_name if from_expr else '',
                                rightAlias=join.this.alias_or_name,
                                preservesUnmatchedLeftRows=side=='LEFT')
            if current: self.input(current,op,1,inputRole='left')
            self.input(right,op,2,inputRole='right'); current = op
        where = expr.args.get('where')
        if where:
            op = self.operation('FILTER',where,condition=sql(where.this))
            if current: self.input(current,op)
            for i, sub in enumerate(where.find_all(exp.Subquery),2):
                self.input(self.query(sub),op,i,kind='SUBQUERY_INPUT')
            current = op
        group = expr.args.get('group')
        aggregates = [sql(a) for p in expr.expressions for a in p.find_all(exp.AggFunc)
                      if a.find_ancestor(exp.Select) is expr and not a.find_ancestor(exp.Window)]
        if group or aggregates:
            op = self.operation('AGGREGATE',expr,
                                groupExpressions=[sql(x) for x in group.expressions] if group else [],
                                aggregateExpressions=aggregates)
            if current: self.input(current,op)
            current = op
        having = expr.args.get('having')
        if having:
            op = self.operation('HAVING',having,condition=sql(having.this))
            if current: self.input(current,op)
            current = op
        project = self.operation('SELECT',expr,
                                 selectExpressions=[sql(x) for x in expr.expressions],
                                 outputAliases=[x.alias_or_name for x in expr.expressions],
                                 rawColumnReferences=sorted(set(sql(c) for c in expr.find_all(exp.Column))),
                                 columnResolution='expressions_preserved; star/ambiguous columns not expanded without schema')
        if current: self.input(current,project)
        for p in expr.expressions:
            for sub in p.find_all(exp.Subquery): self.input(self.query(sub),project,kind='SUBQUERY_INPUT')
            for case in p.find_all(exp.Case):
                rule=self.operation('CASE',case,expressionSql=sql(case))
                self.g.edge(project,'USES_RULE',rule)
        current = project
        if expr.args.get('distinct'):
            op=self.operation('DISTINCT',expr.args['distinct'],deduplication='exact_projected_rows')
            self.input(current,op);current=op
        for arg,kind in [('order','ORDER BY'),('limit','LIMIT')]:
            if expr.args.get(arg):
                op=self.operation(kind,expr.args[arg]);self.input(current,op);current=op
        return current

    def build(self, ast):
        target = self.g.table(self.record['output'],self.record['domain'])
        self.g.table_definitions[target].append(self.record)
        self.g.edge(self.record['key'],'TARGETS_TABLE',target)
        if isinstance(ast, (exp.Create,exp.Insert)):
            final=self.query(ast.expression)
            kind='INSERT' if isinstance(ast,exp.Insert) else 'CREATE TABLE AS'
            write=self.operation(kind,ast,writeMode='append' if kind=='INSERT' else 'create_as_select')
            self.input(final,write)
            self.g.edge(write,'WRITES_TO',target)
        elif isinstance(ast,exp.Delete):
            op=self.operation('DELETE',ast,condition=sql(ast.args.get('where')),
                              mutation='delete matching rows; not a numeric negative contribution')
            self.g.edge(op,'DELETES_FROM',target)
        elif isinstance(ast,exp.TruncateTable):
            op=self.operation('TRUNCATE',ast,mutation='remove all existing rows')
            self.g.edge(op,'CLEARS_TABLE',target)
        else:
            raise ValueError(f'Unsupported statement type: {type(ast).__name__}')
        for table in self.read_tables:
            self.g.edge(self.record['key'],'READS_TABLE',table)
        self.record['readTables'] = sorted(self.g.nodes[k]['properties']['name'] for k in self.read_tables)


def build():
    graph=Graph();errors=[]
    for filename,domain,role in FILES:
        path=ROOT/'sources/sql'/filename
        raw=path.read_bytes();decoded=raw.decode('cp950')
        text=decoded.replace('\r\n','\n').replace('\r','')
        file_key=graph.node('SqlSourceFile',f'{NS}:file:{filename}',name=filename,
                            path=f'sources/sql/{filename}', encoding='cp950',
                            domain=domain, sourceRole=role, rawSql=decoded,
                            normalizedSql=text,sha256=hashlib.sha256(raw).hexdigest())
        graph.edge(graph.root,'HAS_SQL_FILE',file_key)
        for item in statements(text):
            line=text.count('\n',0,item['start'])+1
            status=item['status']
            if status=='active_sql' and role=='alternate_file_reference': status='alternate_file_sql'
            elif status=='active_sql' and role=='auxiliary_monthly_reference': status='auxiliary_reference_sql'
            rec=dict(item,key=f'{NS}:statement:{filename}:L{line}',file=f'sources/sql/{filename}',
                     domain=domain,sourceRole=role,lineStart=line,
                     lineEnd=text.count('\n',0,item['end'])+1,status=status)
            try:
                ast=sqlglot.parse_one(parser_text(item['parserSql']),read='oracle')
                output=ast.this
                if isinstance(output,exp.Schema): output=output.this
                if isinstance(ast,exp.TruncateTable): output=ast.expressions[0]
                assert isinstance(output,exp.Table), type(output)
                rec['output']='.'.join(p.name for p in output.parts).upper()
                rec['statementType']=type(ast).__name__.upper()
                properties={k:v for k,v in rec.items() if k not in ['start','end','parserSql','key']}
                graph.node('SqlStatement',rec['key'],name=f"{rec['output']} · {rec['statementType']} · L{line}",
                           sqlTextKind='original_statement_slice',
                           normalizedForParser='comments blanked; Oracle DB-link suffix removed only for parsing',
                           databaseLinks=sorted(set(re.findall(r'@([A-Za-z0-9_.$]+)',item['parserSql']))),
                           **properties)
                graph.edge(file_key,'HAS_STATEMENT',rec['key'],statementOrder=len(graph.records)+1)
                StatementBuilder(graph,rec).build(ast)
                graph.records.append(rec)
            except Exception as error:
                errors.append({'file':filename,'line':line,'error':str(error)})
    if errors:
        raise RuntimeError(json.dumps(errors,ensure_ascii=False,indent=2))
    # Execution sequence is local to a file and excludes commented definitions.
    for filename,_,_ in FILES:
        active=[r for r in graph.records if r['file'].endswith('/'+filename) and r['status']!='commented_out_sql']
        for left,right in zip(active,active[1:]):
            graph.edge(left['key'],'NEXT_STATEMENT',right['key'],scope='source_file_order')
    for key,domains in graph.table_domains.items():
        defs=graph.table_definitions[key]
        statuses=sorted(set(r['status'] for r in defs))
        props=graph.nodes[key]['properties']
        props.update(domains=sorted(domains), definitionStatuses=statuses,
                     tableKind='staging_output' if defs else 'external_source',
                     hasPrimaryActiveDefinition='active_sql' in statuses,
                     definitionStatus='active_in_primary_sql' if 'active_sql' in statuses else
                     'commented_definition_only' if statuses==['commented_out_sql'] else
                     'alternate_or_auxiliary_definition' if statuses else 'external_definition_not_imported')
    graph.validate()
    plan={'ontologyId':NS,'rootKey':graph.root,'nodes':list(graph.nodes.values()),
          'relationships':list(graph.edges.values()),'sourceFiles':FILES,
          'parser':{'name':'sqlglot','version':sqlglot.__version__,'dialect':'oracle'},
          'limitations':['Static SQL lineage; original staging SQL is never executed.',
                        'Statement order is per source file; deployment order across files is not inferred.',
                        'Column expressions preserved; SELECT * and ambiguous columns require database schema.',
                        'Commented, auxiliary and alternate-file SQL are preserved with explicit status.']}
    # Operators are a parsing intermediate only; Neo4j receives table links.
    from sql_table_links import collapse, LINK_TYPES
    plan=collapse(plan)
    inventory=[{k:v for k,v in r.items() if k not in ['start','end','parserSql','sql']} for r in graph.records]
    out=ROOT/'ontology'
    for filename,obj in [('SQL_lineage_graph_plan.json',plan),('SQL_lineage_statement_inventory.json',inventory)]:
        (out/filename).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'nodes':len(plan['nodes']),'relationships':len(plan['relationships']),
                      'statements':len(graph.records),'statuses':dict(Counter(r['status'] for r in graph.records)),
                      'operationNodes':0,
                      'tableLinks':sum(e['type'] in LINK_TYPES for e in plan['relationships'])},ensure_ascii=False))
    return plan,inventory


if __name__=='__main__':
    build()
