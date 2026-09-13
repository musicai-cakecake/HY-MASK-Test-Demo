import math


def generate_module_randoms(
    seed_primary: int,
    counts_list: list[int],
    range_min: int = 100,  # New: Minimum value of random number (default 100)
    range_max: int = 1000 # New: Maximum value of random number (default 999, left-closed right-open)
) -> list[list[int]]:
    """
    Generate [specified quantity, non-repeating integer, reproducible] random numbers for multiple types of secondary modules
    based on the primary seed.

    Parameter Description:
        seed_primary: Primary random seed (integer)
        counts_list: Number of random numbers required for each type of secondary module [M1, M2, ..., Mn]
        range_min: Lower limit of random number (inclusive), default 100
        range_max: Upper limit of random number (exclusive), default 1000 → corresponding to maximum value 999

    Return Value:
        Nested integer list: [[M1 integers for module 1], [M2 integers for module 2], ...]
    """
    # Initialize an independent main random generator without polluting the global random state
    master_rng = random.Random(seed_primary)
    all_module_nums = []

    # Traverse each module to generate independent random numbers
    for need_count in counts_list:
        # Handle modules that do not require random numbers
        if need_count <= 0:
            all_module_nums.append([])
            continue

        # Generate an independent sub-seed to ensure random numbers between modules do not interfere with each other
        sub_seed = master_rng.randint(0, 10**18)
        sub_rng = random.Random(sub_seed)

        # Verification: The required quantity cannot exceed the total number in the range
        total_numbers = range_max - range_min
        if need_count > total_numbers:
            raise ValueError(
                f"The range [{range_min}, {range_max-1}] only has {total_numbers} non-repeating integers, "
                f"unable to generate {need_count} numbers"
            )

        # Generate [non-repeating] integers (optimal method)
        current_nums = sub_rng.sample(range(range_min, range_max), need_count)
        all_module_nums.append(current_nums)

    return all_module_nums


def select_element_by_seed(data_list, seed):
    """
    Select an element at a fixed position from the list according to a fixed seed
    :param data_list: Sorted fixed-length list
    :param seed: Three-digit random seed (e.g., 400)
    :return: Selected element + corresponding index (for verification)
    """
    # 1. Verify input validity (optional but improves robustness)
    # if not isinstance(data_list, list):
    #     raise ValueError("data_list must be a list type")
    if len(data_list) == 0:
        raise ValueError("data_list cannot be empty")

    # 2. Set random seed (core: the same seed will generate the same random number)
    random.seed(seed)

    # 3. Generate a pseudorandom integer within the range of the list index (0 ~ length of list - 1)
    list_length = len(data_list)
    selected_index = random.randint(0, list_length - 1)

    # 4. Return the selected element and index
    selected_element = data_list[selected_index]
    return selected_element, selected_index


def select_dict_key_by_seed(target_dict, seed):
    """
    Select a fixed key from the dictionary according to a fixed seed
    :param target_dict: Target dictionary (fixed content)
    :param seed: Random seed
    :return: Selected key + corresponding index (for verification)
    """
    # 1. Input validity verification
    if not isinstance(target_dict, dict):
        raise ValueError("target_dict must be a dictionary type")
    if len(target_dict) == 0:
        raise ValueError("target_dict cannot be an empty dictionary")

    # 2. Convert the keys of the dictionary into an ordered list (core: fix the key order of the dictionary)
    key_list = list(target_dict.keys())

    # 3. Set random seed (ensure the same seed generates the same random number)
    random.seed(seed)

    # 4. Generate a random index within the range of the key list and select the corresponding key
    key_list_length = len(key_list)
    selected_index = random.randint(0, key_list_length - 1)
    selected_key = key_list[selected_index]

    return selected_key, selected_index


def select_4_unique_keys_by_seed(target_dict, seed, selected_numbers = 4 ):
    """
    Select 4 non-repeating keys from the dictionary according to a fixed seed,
    the result is exactly the same if the seed is the same
    :param selected_numbers: Number of selections at one time, default 4
    :param target_dict: Target dictionary (fixed content)
    :param seed: Random seed
    :return: List containing 4 non-repeating keys (the order is also fixed by the seed)
    """
    # 1. Strict input validity verification
    if not isinstance(target_dict, dict):
        raise ValueError("target_dict must be a dictionary type!")
    dict_length = len(target_dict)
    if dict_length < 4:
        raise ValueError(f"The length of the dictionary is {dict_length}, less than 4 keys, unable to select 4 non-repeating keys!")
    if dict_length == 0:
        raise ValueError("The target dictionary cannot be empty!")

    # 2. Extract and sort the key list (ensure the absolute fixed order of keys, compatible with all Python versions)
    sorted_key_list = sorted(target_dict.keys())

    # 3. Set random seed (core: fixed seed means fixed random logic)
    random.seed(seed)

    # 4. Select 4 non-repeating keys by sampling without replacement (sample ensures no repetition,
    # and the result is fixed when the seed is fixed)
    selected_4_keys = random.sample(sorted_key_list, k=selected_numbers)

    return selected_4_keys

def select_4_valid_pairs(seed, list_1, list_2, sum_min = 55, sum_max= 79, max_attempts=1000):
    """
    Select 4 valid pairs based on a fixed seed:
    - Select 4 non-repeating a from list_1[55-78], select 4 non-repeating b from list_2[1-13]
    - For each pair a_i + b_i ∈ [55,79] (i.e., list_3=range(55,80))
    :param list_1: Root note list
    :param list_2:  Interval list
    :param sum_max:  Maximum acceptable pitch
    :param sum_min:  Minimum acceptable pitch
    :param seed: Random seed (ensure fixed results)
    :param max_attempts: Maximum number of attempts (avoid extreme loops)
    :return: List of 4 pairs in the format [(a1,b1), (a2,b2), (a3,b3), (a4,b4)]
    :raises RuntimeError: No valid combination found after exceeding the maximum number of attempts
    """

    # 1. Define basic lists (clarify ranges to avoid ambiguity)
    # list_1 = list(range(55, 79))   # 55~78 (24 non-repeating numbers in total)
    # list_2 = list(range(1, 13))    # 1~12 (12 non-repeating numbers in total)
    # sum_min = 55                   # Minimum value of list_3 (left boundary of range(55,80))
    # sum_max = 79                   # Maximum value of list_3 (right boundary of range(55,80), inclusive of 79)

    # 2. Fix random seed (core: all random operations are based on this seed, results are completely fixed)
    random.seed(seed)

    # 3. Pre-generate all valid (a,b) pairs (filter condition: 55 ≤ a+b ≤79)
    valid_pairs = []
    for a in list_1:
        for b in list_2:
            if sum_min <= (a + b) <= sum_max:
                valid_pairs.append((a, b))
    if not valid_pairs:
        raise ValueError("No valid (a,b) pairs exist, please check the list ranges!")

    # 4. Rejection sampling: Select 4 valid pairs with non-repeating a and non-repeating b
    attempts = 0
    while attempts < max_attempts:
        # Randomly shuffle the order of valid pairs (based on seed, the shuffle result is fixed)
        shuffled_valid = valid_pairs.copy()
        random.shuffle(shuffled_valid)

        # Filter 4 pairs that satisfy non-repeating a and non-repeating b
        selected_a = set()
        selected_b = set()
        final_pairs = []
        for a, b in shuffled_valid:
            if a not in selected_a and b not in selected_b:
                final_pairs.append((a, b))
                selected_a.add(a)
                selected_b.add(b)
                # Stop filtering when 4 pairs are collected
                if len(final_pairs) == 4:
                    # Final verification: Ensure the sum of each pair is within the range (double guarantee)
                    for ai, bi in final_pairs:
                        if not (sum_min <= ai + bi <= sum_max):
                            break
                    else:
                        return final_pairs
        attempts += 1

    # Exceeded the maximum number of attempts (theoretically not triggered in this scenario due to sufficient valid pairs)
    raise RuntimeError(f"No 4 pairs meeting the conditions found after {max_attempts} attempts!")


def random_permute(nums, n, seed=42):
    """
    Generate a specified number of non-repeating random full permutations (without recursing all full permutations)
    :param nums: Original list (elements must be different)
    :param n: Number of permutations to generate
    :param seed: Random seed (ensure reproducible results)
    :return: List containing n non-repeating permutations, each permutation is a list type
    """
    # 1. Parameter verification
    if not isinstance(nums, list) or len(nums) == 0:
        return []
    if n <= 0:
        return []

    # Calculate the total number of full permutations (for boundary judgment)
    perm_total = math.factorial(len(nums))
    if n > perm_total:
        print(f"Warning: Requested to generate {n} permutations, but the total number of full permutations is only {perm_total}, all permutations will be returned")
        n = perm_total

    # 2. Initialization configuration
    random.seed(seed)  # Set random seed to ensure reproducible results
    result = []  # Final result list
    seen = set()  # Record generated permutations (stored as tuples because lists are unhashable)
    nums_copy = nums.copy()  # Copy the original list to avoid modifying the original data

    # 3. Loop to generate non-repeating random permutations
    while len(result) < n:
        # Random shuffle (generate a new permutation)
        random.shuffle(nums_copy)
        # Convert to tuple and store in set (deduplication)
        perm_tuple = tuple(nums_copy)
        if perm_tuple not in seen:
            seen.add(perm_tuple)
            result.append(list(perm_tuple))  # Convert back to list to meet requirements

    return result


def generate_random_chain(
        root_seed: int,
        length: int,
        min_val: int = 100,  # Default minimum value 100
        max_val: int = 1000  # Default maximum value 999 (left-closed right-open)
) -> dict:
    """
    Generate a deterministic random number chain: with a fixed root seed, the first n random numbers are independent of the total length l
    Results are stored in a dictionary format of index:random number

    Parameters:
        root_seed: Root random seed (fixed seed means permanently fixed sequence)
        length: Total number of random numbers to generate l
        min_val: Minimum value of random number (inclusive)
        max_val: Maximum value of random number (exclusive, default 999)

    Return:
        Dictionary: {0: 0th random number, 1: 1st random number, ..., length-1: (l-1)th random number}

    Exceptions:
        ValueError is raised when length is less than 1
    """
    # Verify the validity of length
    if not isinstance(length, int) or length < 1:
        raise ValueError("The length of the random number chain must be a positive integer")

    # 🔥 Core: Initialize the [one-time] random generator only with the root seed (ensure fixed sequence)
    rng = random.Random(root_seed)

    # Generate random number chain and store in dictionary (key=sequence index, value=random number)
    random_chain = {}
    for idx in range(length):
        # Generate integer random number within the specified range
        random_num = rng.randint(min_val, max_val - 1)
        random_chain[idx] = random_num

    return random_chain


def generate_2d_random_chain(
        root_seed: int,
        dimensions: list[int],
        min_val: int = 100,  # Minimum random number value 100
        max_val: int = 1000  # Maximum random number value 999
):
    """
    2D deterministic random number chain
    Core guarantee: Fixed root seed + fixed position (i,j) → random number is permanently unchanged, independent of total dimensions [l,k]
    Structure: l categories, each category contains k random numbers
    """
    # Verify dimensions
    if len(dimensions) != 2:
        raise ValueError("Dimensions must be [number of categories l, number per category k]")
    l, k = dimensions
    if not (isinstance(l, int) and l >= 1 and isinstance(k, int) and k >= 1):
        raise ValueError("l and k must be positive integers")

    # 2D random number dictionary
    random_2d = {}

    # Traverse each category i
    for class_idx in range(l):
        random_2d[class_idx] = {}
        # Traverse each sequence number j within the category
        for item_idx in range(k):
            # 🔥 Core: Generate a unique fixed sub-seed for each position (i,j)
            # Formula guarantee: different (i,j) have different sub-seeds, fixed root seed means fixed sub-seeds
            sub_seed = root_seed * 1000000 + class_idx * 1000 + item_idx
            rng = random.Random(sub_seed)

            # Generate random number within fixed range
            random_num = rng.randint(min_val, max_val - 1)
            random_2d[class_idx][item_idx] = random_num

    # Convert dictionary to list
    random_2d_list = []
    for v in random_2d.values():
        random_2d_list.append(v)

    return random_2d, random_2d_list


import random

def generate_3d_random_chain(
    root_seed: int,
    dimensions: list[int],
    min_val: int = 100,   # Minimum random number value 100
    max_val: int = 1000  # Maximum random number value 999
) -> tuple[dict, list[list[list[int]]]]:
    """
    ✅ Correct version: 3D deterministic random number chain
    Core guarantee: Fixed root seed + fixed coordinate (i,j,p) → random number is permanently unchanged, independent of total dimensions [l,k,p]
    3D structure: Number of categories l → number per category k → number of processes p
    Return value: (3D dictionary, 3D list)
    """
    # 1. Dimension verification
    if len(dimensions) != 3:
        raise ValueError("Dimensions must be a list of length 3: [number of categories l, number per category k, number of processes p]")
    l, k, p = dimensions
    if not (isinstance(l, int) and l >= 1 and
            isinstance(k, int) and k >= 1 and
            isinstance(p, int) and p >= 1):
        raise ValueError("l, k, and p must all be positive integers")

    # 2. Generate 3D dictionary (original logic unchanged)
    random_3d = {}
    for class_idx in range(l):
        random_3d[class_idx] = {}
        for item_idx in range(k):
            random_3d[class_idx][item_idx] = {}
            for process_idx in range(p):
                # Unique sub-seed to ensure determinism
                sub_seed = root_seed * 10**9 + class_idx * 10**6 + item_idx * 10**3 + process_idx
                rng = random.Random(sub_seed)
                random_num = rng.randint(min_val, max_val - 1)
                random_3d[class_idx][item_idx][process_idx] = random_num

    # ===================== New: Convert 3D dictionary to 3D list =====================
    random_3d_list = []
    # Traverse all dimensions in order and convert to list
    for class_idx in range(l):
        class_list = []  # 2D list corresponding to a single category
        for item_idx in range(k):
            # Process value list corresponding to a single sequence number
            process_list = [random_3d[class_idx][item_idx][pid] for pid in range(p)]
            class_list.append(process_list)
        random_3d_list.append(class_list)

    # Return both dictionary + 3D list
    return random_3d, random_3d_list


if __name__ == "__main__":

    # Fixed root seed
    ROOT_SEED = 0
    print("3D random chain with root seed: ", ROOT_SEED)

    # 2. Large dimension [3,4]
    chain_3x4x3, chain_3x4x3_list = generate_3d_random_chain(ROOT_SEED, [3, 4, 3])
    print("=== Random number chain of dimension [3,4,3] ===")
    for class_idx, nums in chain_3x4x3.items():
        print(f"Class {class_idx}: {nums}")

    # 2. Large dimension [5,6]
    chain_5x6x4, chain_5x6x4_list = generate_3d_random_chain(ROOT_SEED, [5, 6, 4])
    print("=== Random number chain of dimension [5,6,4] ===")
    for class_idx, nums in chain_5x6x4.items():
        print(f"Class {class_idx}: {nums}")

    chain_5x7x6, chain_5x7x6_list  = generate_3d_random_chain(ROOT_SEED, [5, 7, 6])
    print("=== Random number chain of dimension [5,7,6] ===")
    for class_idx, nums in chain_5x7x6.items():
        print(f"Class {class_idx}: {nums}")