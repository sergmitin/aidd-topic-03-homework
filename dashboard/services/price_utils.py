def calculate_trend(old_price, new_price):
    """
    Определяет направление ценового тренда.

    Возвращает:
        True  — цена выросла
        False — цена упала или осталась прежней
        None  — невозможно определить (одна из цен отсутствует)
    """
    if old_price is None or new_price is None:
        return None
    return new_price > old_price


def quotation_to_float(quotation):
    """
    Конвертирует объект Quotation (units + nano) Tinkoff Invest API в float.

    Tinkoff передаёт цены в виде двух полей:
        units — целая часть
        nano  — дробная часть (миллиардные доли)
    """
    return quotation.units + quotation.nano / 1_000_000_000
