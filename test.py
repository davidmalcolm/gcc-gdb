import gdb

# Hardcoded values corresponding to tree.def
IDENTIFIER_NODE = 1

class Tree:
    """
    Wrapper around a gdb.Value for a tree, with various methods
    corresponding to macros in gcc/tree.h
    """
    def __init__(self, gdbval):
        self.gdbval = gdbval

    def is_nonnull(self):
        return long(self.gdbval)

    def TREE_CODE(self):
        """
        Get gdb.Value corresponding to TREE_CODE (self)
        as per:
          #define TREE_CODE(NODE) ((enum tree_code) (NODE)->base.code)
        """
        return self.gdbval['base']['code']

    def DECL_NAME(self):
        """
        Get Tree instance corresponding to DECL_NAME (self)
        """
        return Tree(self.gdbval['decl_minimal']['name'])

    def TYPE_NAME(self):
        """
        Get Tree instance corresponding to result of TYPE_NAME (self)
        """
        return Tree(self.gdbval['type_common']['name'])

    def IDENTIFIER_POINTER(self):
        """
        Get str correspoinding to result of IDENTIFIER_NODE (self)
        """
        return self.gdbval['identifier']['id']['str'].string()

class TreePrinter:
    "Prints a tree"

    def __init__ (self, gdbval):
        self.gdbval = gdbval
        self.node = Tree(gdbval)

    def to_string (self):
        # like gcc/print-tree.c:print_node_brief
        # #define TREE_CODE(NODE) ((enum tree_code) (NODE)->base.code)
        # tree_code_name[(int) TREE_CODE (node)])
        if long(self.gdbval) == 0:
            return '<tree 0x0>'

        val_TREE_CODE = self.node.TREE_CODE()

        # extern const enum tree_code_class tree_code_type[];
        # #define TREE_CODE_CLASS(CODE)	tree_code_type[(int) (CODE)]

        val_tree_code_type = gdb.parse_and_eval('tree_code_type')
        val_tclass = val_tree_code_type[val_TREE_CODE]

        val_tree_code_name = gdb.parse_and_eval('tree_code_name')
        val_code_name = val_tree_code_name[long(val_TREE_CODE)]
        #print val_code_name.string()

        result = '<%s 0x%x' % (val_code_name.string(), long(self.gdbval))
        if long(val_tclass) == 3: # tcc_declaration
            tree_DECL_NAME = self.node.DECL_NAME()
            if tree_DECL_NAME.is_nonnull():
                 result += ' %s' % tree_DECL_NAME.IDENTIFIER_POINTER()
            else:
                pass # TODO: labels etc
        elif long(val_tclass) == 2: # tcc_type
            tree_TYPE_NAME = Tree(self.gdbval['type_common']['name'])
            if tree_TYPE_NAME.is_nonnull():
                if tree_TYPE_NAME.TREE_CODE() == IDENTIFIER_NODE:
                    result += ' %s' % tree_TYPE_NAME.IDENTIFIER_POINTER()
                elif tree_TYPE_NAME.TREE_CODE() == TYPE_DECL:
                    if tree_TYPE_NAME.DECL_NAME().is_nonnull():
                        result += ' %s' % tree_TYPE_NAME.DECL_NAME().IDENTIFIER_POINTER()
        if self.node.TREE_CODE() == IDENTIFIER_NODE:
            result += ' %s' % self.node.IDENTIFIER_POINTER()
        # etc
        result += '>'
        return result

class GimplePrinter:
    def __init__(self, gdbval):
        self.gdbval = gdbval

    def to_string (self):
        val_gimple_code = self.gdbval['gsbase']['code']
        val_gimple_code_name = gdb.parse_and_eval('gimple_code_name')
        val_code_name = val_gimple_code_name[long(val_gimple_code)]
        return '<%s 0x%x>' % (val_code_name.string(),
                              long(self.gdbval))

def pretty_printer_lookup(gdbval):
    type_ = gdbval.type.unqualified()

    # "tree" is a "(union tree_node *)"

    str_type_ = str(type_)
    if str_type_ in ('union tree_node *', 'tree'):
        return TreePrinter(gdbval)

    if str_type_ in ('union gimple_statement_d *', 'gimple'):
        return GimplePrinter(gdbval)

"""
During development, I've been manually invoking the code in this way:

$ PYTHONPATH=$(pwd) gcc -c foo.c -wrapper gdb,--args
(gdb) break gimple_alloc_stat
(gdb) python import test

then reloading it after each edit like this:
(gdb) python reload(test)

Can then use -v to locate the underlying cc1 command, and wrap it all up thus:

$ PYTHONPATH=$(pwd) gdb \
   --eval-command="break gimple_alloc_stat" \
   --eval-command="python import test" \
   --eval-command="run" \
   --args /usr/libexec/gcc/x86_64-redhat-linux/4.7.2/cc1 -quiet foo.c -quiet -dumpbase foo.c -mtune=generic -march=x86-64 -auxbase foo -o /tmp/ccjOBkfD.s
"""
def register (obj):
    if obj is None:
        obj = gdb

    # Wire up the pretty-printer
    obj.pretty_printers.append(pretty_printer_lookup)

register (gdb.current_objfile ())
print('got here!')
