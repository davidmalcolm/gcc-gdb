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

class CGraphNodePrinter:
    def __init__(self, gdbval):
        self.gdbval = gdbval

    def to_string (self):
        result = '<cgraph_node 0x%x' % long(self.gdbval)
        # symtab_node_name calls lang_hooks.decl_printable_name
        # default implementation (lhd_decl_printable_name) is:
        #    return IDENTIFIER_POINTER (DECL_NAME (decl));
        tree_decl = Tree(self.gdbval['decl'])
        result += ' %s' % tree_decl.DECL_NAME().IDENTIFIER_POINTER()
        result += '>'
        return result

class GimplePrinter:
    def __init__(self, gdbval):
        self.gdbval = gdbval

    def to_string (self):
        val_gimple_code = self.gdbval['gsbase']['code']
        val_gimple_code_name = gdb.parse_and_eval('gimple_code_name')
        val_code_name = val_gimple_code_name[long(val_gimple_code)]
        result = '<%s 0x%x' % (val_code_name.string(),
                               long(self.gdbval))
        result += '>'
        return result

def bb_index_to_str(index):
    if index == 0:
        return 'ENTRY'
    elif index == 1:
        return 'EXIT'
    else:
        return '%i' % index

class BasicBlockPrinter:
    def __init__(self, gdbval):
        self.gdbval = gdbval

    def to_string (self):
        return ('<basic_block 0x%x (%s)>'
                % (long(self.gdbval),
                   bb_index_to_str(long(self.gdbval['index']))))

class CfgEdgePrinter:
    def __init__(self, gdbval):
        self.gdbval = gdbval

    def to_string (self):
        src = bb_index_to_str(long(self.gdbval['src']['index']))
        dest = bb_index_to_str(long(self.gdbval['dest']['index']))
        return ('<edge_def 0x%x (%s -> %s)>'
                % (long(self.gdbval), src, dest))

class Rtx:
    def __init__(self, gdbval):
        self.gdbval = gdbval

    def GET_CODE(self):
        return self.gdbval['code']

def GET_RTX_LENGTH(code):
    val_rtx_length = gdb.parse_and_eval('rtx_length')
    return long(val_rtx_length[code])

def GET_RTX_NAME(code):
    val_rtx_name = gdb.parse_and_eval('rtx_name')
    return val_rtx_name[code].string()

def GET_RTX_FORMAT(code):
    val_rtx_format = gdb.parse_and_eval('rtx_format')
    return val_rtx_format[code].string()

class RtxPrinter:
    def __init__(self, gdbval):
        self.gdbval = gdbval
        self.rtx = Rtx(gdbval)

    def to_string (self):
        """
        For now, a cheap kludge: invoke the inferior's print
        function to get a string to use the user, and return an empty
        string for gdb
        """
        # We use print_inline)rtx to avoid trailing newline
        gdb.execute('call print_inline_rtx(stderr, %s, 0)'
                    % long(self.gdbval))
        return ''

        # or by hand; based on gcc/print-rtl.c:print_rtx
        result = ('<rtx_def 0x%x'
                  % (long(self.gdbval)))
        code = self.rtx.GET_CODE()
        result += ' (%s' % GET_RTX_NAME(code)
        format_ = GET_RTX_FORMAT(code)
        for i in range(GET_RTX_LENGTH(code)):
            print format_[i]
        result += ')>'
        return result

class PassPrinter:
    def __init__(self, gdbval):
        self.gdbval = gdbval

    def to_string (self):
        result = '<opt_pass 0x%x' % long(self.gdbval)
        if long(self.gdbval):
            result += (' "%s"(%i)'
                       % (self.gdbval['name'].string(),
                          long(self.gdbval['static_pass_number'])))
        result += '>'
        return result

# TODO:
#   vec
#   hashtab


def pretty_printer_lookup(gdbval):
    type_ = gdbval.type.unqualified()

    # "tree" is a "(union tree_node *)"

    str_type_ = str(type_)
    if str_type_ in ('union tree_node *', 'tree'):
        return TreePrinter(gdbval)

    if str_type_ in ('struct cgraph_node *', ):
        return CGraphNodePrinter(gdbval)

    if str_type_ in ('union gimple_statement_d *', 'gimple'):
        return GimplePrinter(gdbval)

    if str_type_ in ('struct basic_block_def *', 'basic_block', ):
        return BasicBlockPrinter(gdbval)

    if str_type_ in ('struct edge_def *', ):
        return CfgEdgePrinter(gdbval)

    if str_type_ in ('struct rtx_def *', ):
        return RtxPrinter(gdbval)

    if str_type_ in ('struct opt_pass *', ):
        return PassPrinter(gdbval)


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

Other interesting breakpoints:
   break expand_gimple_stmt
(for watching gimple become rtl and thus pretty-printing both)
"""
def register (obj):
    if obj is None:
        obj = gdb

    # Wire up the pretty-printer
    obj.pretty_printers.append(pretty_printer_lookup)

register (gdb.current_objfile ())
print('got here!')
