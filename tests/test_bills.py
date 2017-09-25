from .common import assert_dataservice_processor_data


def test_bills():
    assert_dataservice_processor_data("bills", "kns_bill",
                                      [{'BillID': 5, 'KnessetNum': 1, 'Name': 'חוק שכר חברי הכנסת, התש"ט-1949'},
                                       {'BillID': 20, 'KnessetNum': 7, 'Name': 'חוק מקצועות רפואיים (אגרות), התשל"א-1971'},
                                       {'BillID': 15752, 'KnessetNum': 16, 'Name': 'חוק רשות הספנות והנמלים, התשס"ד-2004'}])

def test_bill_names():
    assert_dataservice_processor_data("bills", "kns_billname",
                                      [{'BillNameID': 1, 'BillID': 135664,
                                        'Name': 'הצעת חוק בתי דין רבניים (קיום פסקי דין של גירושין) (תיקון - הרחבת אמצעי האכיפה כנגד סרבן גט), התשס"ו-2006'},
                                       {'BillNameID': 2, 'BillID': 143609,
                                        'Name': 'חוק הביטוח הלאומי (תיקון מס\' 87), התשס"ו-2006'},
                                       {'BillNameID': 3, 'BillID': 142356,
                                        'Name': 'הצעת חוק חופש המידע (תיקון  מס\' 5), התשס"ז-2007'}])
