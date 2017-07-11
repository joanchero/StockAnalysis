#include "Python.h"
#include "object.h"

#ifdef WITH_THREAD
#include "pythread.h"
#endif

PyObject *
GET_DICTIONARY(PyObject *ob) {

        PyObject **dictptr = _PyObject_GetDictPtr(ob);
        PyObject *dict = NULL;

        if (dictptr == NULL) {

            if (PyInstance_Check(ob))
		dict = ((PyInstanceObject *)ob)->in_dict;

            if (dict == NULL) {
                PyErr_SetString(PyExc_AttributeError,
                                "This object has no __dict__");
                return NULL;
            }

        } else {
            dict = *dictptr;
            if (dict == NULL)
                *dictptr = dict = PyDict_New();
        }

        Py_XINCREF(dict);
        return dict;
}

long
_get_py_thread_ident() {
#ifdef WITH_THREAD
    return PyThread_get_thread_ident();
#else
    return 1;
#endif
}
