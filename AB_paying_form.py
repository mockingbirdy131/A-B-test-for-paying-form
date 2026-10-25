import pandas as pd
from statsmodels.stats.proportion import proportions_ztest

#=================== Data ===================
users = pd.read_excel('dannye-dlia-keisa-po-pa.xlsx', sheet_name='Пользователи')
payments = pd.read_excel('dannye-dlia-keisa-po-pa.xlsx', sheet_name='Платежи')

# =================== Cleaning ===================
cleaning = open('cleaning.txt', 'w', encoding='utf-8')

def clean(df, description, func):
    before = len(df)
    df = func(df)
    after = len(df)
    print(f'{description}: удалено {before - after} строк (было {before}, стало {after})', file = cleaning)
    return df

users = clean(users, 'пустые user_id', lambda d: d.dropna(subset=['user_id']))
users = clean(users, 'некорректные группы', lambda d: d[d['group'].isin(['A', 'B'])])
users = clean(users, 'некорректный возраст', lambda d: d[~((d['age'].isnull()) | (d['age'] < 14) | (d['age'] > 121))]) # с 14 лет по закону можно платить, а самый старый человек в России - Яха Хашагова (1905)
users = clean(users, 'дубликаты по user_id', lambda d: d.drop_duplicates(subset='user_id', keep='first'))
cleaning.write('\n')
payments = clean(payments, 'пустые payment_id', lambda d: d.dropna(subset=['payment_id']))
payments = clean(payments, 'некорректные группы', lambda d: d[d['group'].isin(['A', 'B'])])
payments = clean(payments, 'дубликаты по payment_id', lambda d: d.drop_duplicates(subset='payment_id', keep='first'))
cleaning.write('\n')
payments = clean(payments, 'шаг 2 без шага 1', lambda d: d[~((d['step2_entered'].notna()) & (d['step1_opened'].isnull()))])
payments = clean(payments, 'шаг 3 без предыдущих', lambda d: d[~((d['step3_confirmed'].notna()) & (d['step2_entered'].isnull()))])
payments = clean(payments, 'шаг 4 без предыдущих', lambda d: d[~((d['step4_success'].notna()) & (d['step3_confirmed'].isnull()))])
cleaning.write('\n')
start = pd.Timestamp('2024-04-01')
end = pd.Timestamp('2024-05-01')  # чтобы 30 апреля входило полностью
payments = clean(payments, 'неверная дата в шаге 1', 
                 lambda d: d[~((d['step1_opened'].notna()) & ((d['step1_opened'] < start) | (d['step1_opened'] >= end)))])
payments = clean(payments, 'неверная дата в шаге 2', 
                 lambda d: d[~((d['step2_entered'].notna()) & ((d['step2_entered'] < start) | (d['step2_entered'] >= end)))])
payments = clean(payments, 'неверная дата в шаге 3', 
                 lambda d: d[~((d['step3_confirmed'].notna()) & ((d['step3_confirmed'] < start) | (d['step3_confirmed'] >= end)))])
payments = clean(payments, 'неверная дата в шаге 4', 
                 lambda d: d[~((d['step4_success'].notna()) & ((d['step4_success'] < start) | (d['step4_success'] >= end)))])

# =================== Analysis ===================
analysis = open('analysis.txt', 'w', encoding='utf-8')
df = users.merge(payments, on=['user_id', 'group'], how='left') # один пользователь мог платить несколько раз

cr14 = df.groupby('group').apply(
    lambda x: round(100 * (x['step4_success'].notna()).sum() / (x['step1_opened'].notna()).sum(), 2)
)
cr12 = df.groupby('group').apply(
    lambda x: round(100 * (x['step2_entered'].notna()).sum() / (x['step1_opened'].notna()).sum(), 2)
)
cr23 = df.groupby('group').apply(
    lambda x: round(100 * (x['step3_confirmed'].notna()).sum() / (x['step2_entered'].notna()).sum(), 2)
)
cr34 = df.groupby('group').apply(
    lambda x: round(100 * (x['step4_success'].notna()).sum() / (x['step3_confirmed'].notna()).sum(), 2)
)
print('1->4\n', cr14, file = analysis)
print('1->2\n', cr12, file = analysis)
print('2->3\n', cr23, file = analysis)
print('3->4\n', cr34, file = analysis)

step1 = df.groupby('group').apply(
    lambda x: (x['step1_opened'].notna()).sum() 
)
step2 = df.groupby('group').apply(
    lambda x: (x['step2_entered'].notna()).sum() 
)
step3 = df.groupby('group').apply(
    lambda x: (x['step3_confirmed'].notna()).sum() 
)
step4 = df.groupby('group').apply(
    lambda x: (x['step4_success'].notna()).sum() 
)

nobs = [step1['A'], step1['B']]
success = [step4['A'], step4['B']]
z, p_value = proportions_ztest(success, nobs, alternative='smaller')
print(f'1-4: z = {z:.3f}, p_value = {p_value:.16f}', file = analysis)

success = [step2['A'], step2['B']]
z, p_value = proportions_ztest(success, nobs, alternative='smaller')
print(f'1-2: z = {z:.3f}, p_value = {p_value:.16f}', file = analysis)

nobs = success
success = [step3['A'], step3['B']]
z, p_value = proportions_ztest(success, nobs, alternative='smaller')
print(f'2-3: z = {z:.3f}, p_value = {p_value:.16f}', file = analysis)

nobs = success
success = [step4['A'], step4['B']]
z, p_value = proportions_ztest(success, nobs, alternative='smaller')
print(f'3-4: z = {z:.3f}, p_value = {p_value:.16f}', file = analysis)
