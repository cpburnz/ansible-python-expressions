# encoding: utf-8
"""
This module provides the *expr* action which allows use of ``eval()``
to execute expressions and the use of ``exec()`` to execute statements.
"""

__author__ = "Caleb P. Burns"
__copyright__ = "Copyright © 2015 Caleb P. Burns"
__created__ = "2015-10-17"
__email__ = "cpburnz@gmail.com"
__license__ = "GPLv3"
__updated__ = "2015-10-19"
__version__ = "1.0.0"

import ast
import re
import sys
import traceback

from ansible import utils
from ansible.callbacks import vv
from ansible.runner.return_data import ReturnData

if sys.version_info.major == 2:
	string_types = basestring

	def iteritems(dictionary):
		return dictionary.iteritems()

	def iterkeys(dictionary):
		return dictionary.iterkeys()

else:
	string_types = str

	def iteritems(dictionary):
		return dictionary.items()

	def iterkeys(dictionary):
		return dictionary.keys()

#: Detect an import statement of the form "from ... import ...".
MATCH_FROM_IMPORT = re.compile(r'^(?P<from>from\b)?.+\bimport\b')

#: Detect an import statement of the form "import ...".
MATCH_IMPORT = re.compile(r'^(?P<import>import\b)?(?!.+\bimport\b)')


class ActionModule(object):
	"""
	The ``ActionModule`` class implements the *eval* action for evaluating
	python expressions.
	"""

	TRANSFERS_FILES = False

	def __init__(self, runner):
		"""
		Initializes the ``ActionModule`` instance.

		*runner* (``ansible.runner.Runner``) is the core API interface to
		Ansible.
		"""

		self.runner = runner
		"""
		*runner* (``ansible.runner.Runner``) is the core API interface to
		Ansible.
		"""

	def _import_modules(self, modules):
		"""
		Import the specified modules.

		*modules* (``list`` of ``tuple``) contains the modules and their
		names to import.

		Returns the imported modules and names (``dict``)
		"""
		namespace = {}

		for module, spec in modules:
			if isinstance(spec, dict):
				# Import the module, the spec defines the from-list.
				result = __import__(module, globals(), fromlist=list(iterkeys(spec)), level=0)
				namespace.update((alias or name, getattr(result, name)) for name, alias in iteritems(spec))

			elif spec is not None:
				# Import the module, the spec is its alias.
				__import__(module, globals(), level=0)
				namespace[spec] = sys.modules[module]

			else:
				# Import the module.
				namespace[module.split('.', 1)[0]] = __import__(module, globals(), level=0)

		return namespace

	def _parse_imports(self, imports):
		"""
		Parses the import strings.

		*imports* (``list`` of ``str``) contains the import strings.

		Returns the modules to import (``list`` of ``tuples``).
		"""
		if isinstance(imports, string_types):
			imports = [imports]
		elif not isinstance(imports, list):
			raise TypeError("imports:{!r} is not a string or list.".format(imports))

		lines = [line.strip() for lines in imports for line in lines.split(';')]

		import_specs = []
		for line in lines:
			# Format: "import ..."
			match = MATCH_IMPORT.match(line)
			if match is not None:
				if match.group('import') is None:
					line = "import {}".format(line)

				# Parse import statement.
				tree = ast.parse(line)
				for module in tree.body[0].names:
					import_specs.append((module.name, module.asname))

				# Process next line.
				continue

			# Format: "from ... import ..."
			match = MATCH_FROM_IMPORT.match(line)
			if match is not None:
				if match.group('from') is None:
					line = "from {}".format(line)

				# Parse import statement.
				tree = ast.parse(line)
				module = tree.body[0]
				import_specs.append((module.module, {name.name: name.asname for name in module.names}))

				# Process next line.
				continue

			raise ValueError("line:{!r} is not an import statement.".format(line))

		return import_specs

	def run(self, conn, tmp, module_name, module_args, inject, complex_args=None, **kwargs):
		"""
		Run the action.

		*module_args* (``str``) contains the action arguments when passed as
		a string. E.g.,

		.. code:: yaml

		  - expr: eval=...

		*inject* (``dict``) contains the current set of Ansible variables.

		*complex_args* (``dict``) contains the action arguments when passed
		as a dictionary. E.g.,::

		.. code:: yaml

		  - expr:
		      eval: ...

		Returns the result of the action (``ansible.runner.return_data.ReturnData``).
		"""
		if self.runner.noop_on_check(inject):
			# Skip this action in check mode.
			return ReturnData(conn=conn, result={'skipped': True})

		# Load arguments.
		args = {}
		args.update(utils.parse_kv(module_args))
		if complex_args is not None:
			args.update(complex_args)

		# The local context the expression will be evaluated in.
		local = {}

		# Import specified modules.
		imports = args.get('imports')
		if imports is not None:
			try:
				imports = self._parse_imports(imports)
			except Exception as e:
				vv(traceback.format_exc())
				return ReturnData(conn=conn, result={'failed': True, 'imports': imports, 'msg': "Invalid imports: {}".format(e)})
			try:
				imports = self._import_modules(imports)
			except Exception as e:
				vv(traceback.format_exc())
				return ReturnData(conn=conn, result={'failed': True, 'imports': imports, 'msg': "Import error: {}".format(e)})
			local.update(imports)

		# Expose specified variables.
		vars = args.get('vars')
		if vars is not None:
			try:
				local.update(vars)
			except Exception as e:
				vv(traceback.format_exc())
				return ReturnData(conn=conn, result={'failed': True, 'vars': vars, 'msg': "Invalid vars: {}".format(e)})

		# Get command.
		if 'eval' in args and 'exec' in args:
			return ReturnData(conn=conn, result={'failed': True, 'eval': args['eval'], 'exec': args['exec'], 'msg': "eval and exec are mutually exclusive."})

		elif 'eval' in args:
			key = 'eval'

			# Evaluate expression.
			expr = args['eval']
			try:
				result = eval(expr, inject, local)
			except Exception as e:
				vv(traceback.format_exc())
				return ReturnData(conn=conn, result={'failed': True, 'eval': expr, 'msg': "Eval error: {}".format(e)})

		elif 'exec' in args:
			key = 'exec'

			# Get return expression.
			returns = args.get('returns')
			if returns is None:
				return ReturnData(conn=conn, result={'failed': True, 'msg': "returns is required for exec."})

			# Execute statements.
			expr = args['exec']
			try:
				exec(expr, inject, local)
			except Exception as e:
				vv(traceback.format_exc())
				return ReturnData(conn=conn, result={'failed': True, 'exec': expr, 'msg': "Exec error: {}".format(e)})

			# Get return value.
			try:
				result = eval(returns, inject, local)
			except Exception as e:
				vv(traceback.format_exc())
				return ReturnData(conn=conn, result={'failed': True, 'returns': returns, 'msg': "Return error: {}".format(e)})

		# Returns the action result.
		return ReturnData(conn=conn, result={'failed': False, 'changed': False, key: result})