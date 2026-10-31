"""Business-only dictionary; no existing graph nodes are reused or copied."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def build():
    # Stable product codes are the application join contract, not graph edges.
    products = [
        ('deposit', '存款', '客戶在銀行持有的存款。AUM衡量存款餘額；Income衡量存款整體利息收入，不將總利收重複分配至各子類。', 'aggregate_scope'),
        ('bank_insurance', '銀行保險', '銀行通路保險業務。AUM衡量原始投資金額；Income衡量相關收入，收入是否重複計入仍待確認。', 'overlap_unresolved'),
        ('bank_fund', '銀行基金', '銀行通路的基金業務，涵蓋客戶持有資產與相關收入。', 'inferred'),
        ('bank_etf', '銀行ETF', '銀行通路的指數股票型基金業務，涵蓋客戶持有資產與相關收入。', 'inferred'),
        ('bank_overseas_stock', '銀行海外股票', '銀行通路的海外股票業務，涵蓋客戶持有資產與相關收入。', 'inferred'),
        ('bank_bond_trust', '海外債券（信託）', '以信託方式持有的海外債券業務，涵蓋客戶持有市值與相關信託收入。', 'inferred'),
        ('bank_bond_proprietary', '海外債券（自營）', '銀行自營通路的海外債券業務，涵蓋客戶持有資產與相關收入；兩側業務對應仍屬推論。', 'inferred'),
        ('bank_collective_account', '集合管理帳戶', '集合管理帳戶業務。AUM衡量客戶持有資產；Income的獨立業務定義待確認，不代表已確認計入獨立收入。', 'pending_confirmation'),
        ('bank_structured_offshore', '銀行境外結構型商品', '銀行通路的境外結構型商品業務，涵蓋客戶持有資產與相關收入。', 'inferred'),
        ('bank_planned_trust', '規劃型信託', '規劃型信託業務，涵蓋受託管理資產及相關管理、成立與借券收入。', 'inferred'),
        ('bank_trust_custody', '信託保管', '信託保管業務，涵蓋保管資產與保管費收入。', 'inferred'),
        ('securities_bond', '證券複委託債券', '證券通路的複委託債券業務，涵蓋部位估值與交易手續費收入。', 'inferred'),
        ('securities_structured', '證券複委託結構型商品', '證券通路的複委託結構型商品業務，涵蓋客戶持有資產與相关收入。', 'inferred'),
        ('securities_fund', '證券複委託基金', '證券通路的複委託基金業務，涵蓋客戶持有資產與交易費收入。', 'inferred'),
        ('securities_foreign_stock', '證券複委託外國股票', '證券通路的複委託外國股票業務，涵蓋客戶持有資產與淨手續費收入；淨收入可能為負值。', 'inferred'),
    ]
    metrics = [
        ('aum_total_month_end', '月底總AUM', '指定月份各分類最新可用日期的存款與投資資產合計。此月底衡量定義仍為草案。', 'draft', 'aum'),
        ('aum_deposit_month_end', '月底存款AUM', '月底衡量的銀行存款餘額。', 'inferred', 'aum'),
        ('aum_investment_month_end', '月底投資AUM', '月底衡量的銀行及證券通路投資資產合計。', 'inferred', 'aum'),
        ('aum_bank_investment_month_end', '月底銀行投資AUM', '月底衡量的銀行通路投資資產。', 'inferred', 'aum'),
        ('aum_securities_month_end', '月底證券AUM', '月底衡量的證券通路投資資產。', 'inferred', 'aum'),
        ('aum_insurance_month_end', '月底保險AUM', '月底衡量的銀行保險原始投資金額。', 'inferred', 'aum'),
        ('income_total_customer_month', '每客戶每月總收入', '每位客戶每月的手續費類收入與利息收入合計，業務定義尚待正式確認。', 'pending_confirmation', 'income'),
        ('fee_income', '手續費類收入', '包含手續費、客戶貢獻度與部分損益的收入分類。', 'inferred', 'income'),
        ('bank_fee_income', '銀行手續費類收入', '銀行通路歸入手續費類的收入。', 'inferred', 'income'),
        ('securities_fee_income', '證券手續費類收入', '證券通路歸入手續費類的收入。', 'inferred', 'income'),
        ('interest_income', '利息收入', '存款與放款業務的利息收入。', 'inferred', 'income'),
        ('deposit_interest_income', '存款利收', '存款業務整體的利息收入。', 'inferred', 'income'),
    ]
    nodes = []
    for code, name, definition, status in products:
        props = dict(productCode=code, name=name, definition=definition, status=status,
                     aumStatus='inferred', incomeStatus='pending_confirmation' if code == 'bank_collective_account' else 'overlap_unresolved' if code == 'bank_insurance' else 'inferred')
        nodes.append(dict(kind='product', properties=props))
    for code, name, definition, status, domain in metrics:
        nodes.append(dict(kind=domain, properties=dict(metricCode=code, name=name, definition=definition, status=status)))
    # These values define properties of the Customer concept, not customer records.
    nodes.append(dict(kind='customer', properties=dict(
        conceptCode='customer', name='客戶', status='model_confirmed',
        definition='AUM與收入指標共同的客戶衡量對象。此節點描述客戶概念與基本屬性，並非任何一位實際客戶。',
        customerId='用於識別衡量對象的客戶識別碼。各來源的識別種類與跨來源對照尚待確認，不表示已建立統一客戶身分。',
        customerName='客戶姓名或名稱；來源未提供時可缺值，委託人名稱須依來源角色解讀。',
        customerNumber='選用的來源客戶編號；與客戶識別碼分開理解，不保證可跨來源對照。',
    )))
    edges = []
    for code, *_ in products:
        aum = 'aum_deposit_month_end' if code == 'deposit' else 'aum_insurance_month_end' if code == 'bank_insurance' else 'aum_securities_month_end' if code.startswith('securities_') else 'aum_bank_investment_month_end'
        income = 'deposit_interest_income' if code == 'deposit' else 'securities_fee_income' if code.startswith('securities_') else 'bank_fee_income'
        edges.append(dict(source=code, target=aum, type='PB_AUM_MEASURED_BY'))
        edges.append(dict(source=code, target=income, type='PB_INCOME_PENDING' if code == 'bank_collective_account' else 'PB_INCOME_MEASURED_BY'))
    for domain, pairs in {
        'aum': [('aum_deposit_month_end', 'aum_total_month_end'), ('aum_investment_month_end', 'aum_total_month_end'), ('aum_bank_investment_month_end', 'aum_investment_month_end'), ('aum_securities_month_end', 'aum_investment_month_end'), ('aum_insurance_month_end', 'aum_bank_investment_month_end')],
        'income': [('interest_income', 'income_total_customer_month'), ('fee_income', 'income_total_customer_month'), ('bank_fee_income', 'fee_income'), ('securities_fee_income', 'fee_income'), ('deposit_interest_income', 'interest_income')],
    }.items():
        edges.extend(dict(source=a, target=b, type=f'PB_{domain.upper()}_ROLLS_UP_TO') for a, b in pairs)
    edges.extend(dict(source=code, target='customer', type='PB_MEASURES_CUSTOMER')
                 for code, *_ in metrics)
    plan = dict(nodes=nodes, relationships=edges)
    (HERE / 'concept_graph.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(nodes=len(nodes), relationships=len(edges))))


if __name__ == '__main__':
    build()
