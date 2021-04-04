def import_class(name):
    components = name.split('.')
    print(components[0])
    mod = __import__(components[0])  # import return model
    print(mod)
    #可以使用__import__函数实现模块的延迟导入
    for comp in components[1:]:
        mod = getattr(mod, comp)
    print(mod)
    return mod


# print(vars(import_class("feeders.feeder.Feeder")))
import time
print(time.localtime())
import shutil
Model = import_class("model.shift_gcn.Model") # 载入模型
import inspect
print(inspect.getfile(Model))
b = shutil.copy2(inspect.getfile(Model), "a")
