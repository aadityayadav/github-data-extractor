
# def maxMin(operations, x):
#     elements = set()
#     products = []
#     for i in range(len(operations)):
#         if operations[i] == 'push':
#             elements.add(x[i])
#         elif operations[i] == 'pop':
#             elements.remove(x[i])
#         # print(elements)
#         products.append(max(elements) * min(elements))
#     return products




# operations = ['push', 'push', 'push', 'pop']
# x = [1, 2, 3, 1]
# maxMin(operations, x)

def maxMin(operations, x):
    elements = set()
    max_val = float('-inf')
    min_val = float('inf')
    products = []

    for i in range(len(operations)):
        if operations[i] == 'push':
            max_val = max(max_val, x[i])
            min_val = min(min_val, x[i])
            elements.add(x[i])
        else:
            if x[i] == max_val:
                max_val = max(elements) 
            if x[i] == min_val:
                min_val = min(elements)
            elements.remove(x[i])

        products.append(max_val * min_val)

    return products


operations = ['push', 'push', 'push', 'pop']
x = [1, 2, 3, 1]
result = maxMin(operations, x)
print(result)