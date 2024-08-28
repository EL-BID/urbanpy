import urbanpy as up
from shapely import wkt
import time
from functools import wraps


def timeit(func):
    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        print(f"Function {func.__name__}{args} took {total_time:.4f} seconds")
        return result

    return timeit_wrapper


@timeit
def old():
    resources_df = up.download.search_hdx_dataset("uruguay")
    pop = up.download.get_hdx_dataset(resources_df, 0)
    print(pop.shape)


@timeit
def new():
    bb = "POLYGON((-56.722 -34.1614, -55.3441 -34.1614, -55.3441 -34.8374, -56.722 -34.8374, -56.722 -34.1614))"
    mask = wkt.loads(bb)
    resources_df = up.download.search_hdx_dataset("uruguay")
    pop = up.download.get_hdx_dataset(resources_df, 0, mask=mask)
    print(pop.shape)


if __name__ == "__main__":
    old()  # Function old() took 13.7975 seconds
    new()  # Function new() took 29.8726 seconds
