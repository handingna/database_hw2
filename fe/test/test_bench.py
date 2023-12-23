from fe.bench.run import run_bench


def test_bench():
    try:
        run_bench()
    except Exception as e:
        print("Exception in test_bench:", str(e))
        assert 200 == 100,"test_bench过程出现异常"
