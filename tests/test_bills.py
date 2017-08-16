from .common import assert_dataservice_processor_data


def test_bills():
    assert_dataservice_processor_data("bills", "bills",
                                      [{'id': 5, 'kns_num': 1, 'name': 'חוק שכר חברי הכנסת, התש"ט-1949'},
                                       {'id': 20, 'kns_num': 7, 'name': 'חוק מקצועות רפואיים (אגרות), התשל"א-1971'},
                                       {'id': 15752, 'kns_num': 16, 'name': 'חוק רשות הספנות והנמלים, התשס"ד-2004'}])

def test_bill_names():
    assert_dataservice_processor_data("bills", "bill-names",
                                      [{'id': 1, 'bill_id': 135664,
                                        'name': 'הצעת חוק בתי דין רבניים (קיום פסקי דין של גירושין) (תיקון - הרחבת אמצעי האכיפה כנגד סרבן גט), התשס"ו-2006'},
                                       {'id': 2, 'bill_id': 143609,
                                        'name': 'חוק הביטוח הלאומי (תיקון מס\' 87), התשס"ו-2006'},
                                       {'id': 3, 'bill_id': 142356,
                                        'name': 'הצעת חוק חופש המידע (תיקון  מס\' 5), התשס"ז-2007'}])
