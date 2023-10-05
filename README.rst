.. note::
  To get a better overview visit `JSONtools documentation webpage <https://santibreo.github.io/jsontools/index.html>`_.


#########
JSONtools
#########

Here are all the tools that I found myself writing many times to make minimal changes in JSON structured data.

From now on, if I have to write something to manipulate any *jsonified* API response I will try to make it general enough to keep adding functionalities here.


*****************
How to contribute
*****************

If anyone is willing to contribute that is always good news. The only rule is that you can only use Python *builtins* because this package must be small enough to not have any dependency (so you can install it and use as any other *builtin tools*).


****************************************
JSON related tools this is not replacing
****************************************

While working with JSONs I have found many tools that I really like and use, like:

* `jq <https://jqlang.github.io/jq/manual/>`_: Fast and furious command line utility to query JSON structured data.
* `orjson <https://github.com/ijl/orjson>`_: Like *builtin* `json <https://docs.python.org/es/3/library/json.html>`_ library but much faster and supporting many more Python types.

This is not replacing any of those tools, it does not pretend being so powerful. This is just a collection of handy functions.
