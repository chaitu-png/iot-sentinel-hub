def test_empty(): assert list(process_batch_v2([])) == []
def test_none(): assert list(process_batch_v2([None])) == ['']
