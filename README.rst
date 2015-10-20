
*expr*: Ansible Python Expressions
==================================

When you prevent functionality, someone will find a way around it. The *expr*
action plugin allows use of ``eval()`` (`2 <https://docs.python.org/2/library/functions.html#eval>`_,
`3 <https://docs.python.org/3/library/functions.html#eval>`_) to evaluate
Python expressions and use of ``exec()`` (`2 <https://docs.python.org/2/reference/simple_stmts.html#the-exec-statement>`_,
`3 <https://docs.python.org/3/library/functions.html#exec>`_) to execute
Python statements (unlike Jinja2).



Tutorial
--------

A single expression can be evaluated as:

.. code-block:: yaml

	---
	- hosts: localhost
	  vars:
	    date_format: "%Y-%m-%d %H:%M:%S"
	  tasks:
	  - expr:
	      eval: datetime.datetime.now().strftime(date_format)
	      imports: datetime
	    register: result
	  - debug:
	      msg: "{{ result.eval }}"

Multiple statments can be executed as:

.. code-block:: yaml

	---
	- hosts: localhost
	  vars:
	    date_format: "%Y-%m-%d %H:%M:%S"
	  tasks:
	  - expr:
	      exec: |
	        import datetime
	        now = datetime.datetime.now().strftime(date_format)
	      returns: now
	    register: result
	  - debug:
	      msg: "{{ result.exec }}"

See `library/expr`_ for the documentation on *expr* action. See
`test/eval.yml`_ and `test/exec.yml`_ for more examples.



Including
---------

To use the *expr* action plugin with a set of playbooks:

- Copy `action_plugins/expr.py`_ into ``./action_plugins/`` (relative to the
  playbooks).
- Copy `library/expr`_ into ``./library/`` (relative to the playbooks).

See `Distributing Plugins`_ for some vague details.

.. _`action_plugins/expr.py`: action_plugins/expr.py
.. _`library/expr`: library/expr
.. _`Distributing Plugins`: http://docs.ansible.com/ansible/developing_plugins.html#distributing-plugins



Source
------

The source code for *expr* is available from the GitHub repo
`cpburnz/ansible-python-expressions`_.

.. _`cpburnz/ansible-python-expressions`: https://github.com/cpburnz/ansible-python-expressions



License
-------

*expr* is licensed under the `GNU General Public License Version 3`_ because
`Ansible is licensed`_ under the GPLv3. See `LICENSE`_, the `Quick Guide`_, or
the `FAQ`_ for more information.

.. _`GNU General Public License Version 3`: http://www.gnu.org/licenses/gpl-3.0.html
.. _`Ansible is licensed`: https://github.com/ansible/ansible/blob/devel/COPYING
.. _`LICENSE`: LICENSE
.. _`Quick Guide`: http://www.gnu.org/licenses/quick-guide-gplv3.en.html
.. _`FAQ`: http://www.gnu.org/licenses/gpl-faq.en.html