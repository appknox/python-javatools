# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, see
# <http://www.gnu.org/licenses/>.



"""
Utility script and module for inspecting binary java class files

Let's pretend to be the javap tool shipped with many Java SDKs

author: Christopher O'Brien  <obriencj@gmail.com>
license: LGPL
"""



HEADER = 0
PUBLIC = 1
PACKAGE = 3
PRIVATE = 7



def should_show(options, member):

    """ whether to show a member by its access flags and the show
    option. There's probably a faster and smarter way to do this, but
    eh. """

    show = options.show
    if show == PUBLIC:
        return member.is_public()
    elif show == PACKAGE:
        return member.is_public() or member.is_protected()
    elif show == PRIVATE:
        return True



def print_field(options, field):

    if options.indent:
        print "   ",

    print "%s;" % field.pretty_descriptor()

    if options.sigs:
        print "  Signature:", field.get_signature()

    if options.verbose:
        cv = field.get_constantvalue()
        if cv is not None:
            t,v = field.cpool.pretty_const(cv)
            if t:
                print "  Constant value:", t, v
        print



def print_method(options, method):
    import javaclass.opcodes as opcodes

    if options.indent:
        print "   ",

    print "%s;" % method.pretty_descriptor()

    if options.sigs:
        print "  Signature:", method.get_signature()

    code = method.get_code()
    if options.disassemble and code:

        print "  Code:"

        if options.verbose:
            # the arg count is the number of arguments consumed from
            # the stack when this method is called. non-static methods
            # implicitly have a "this" argument that's not in the
            # descriptor
            argsc = len(method.get_arg_type_descriptors())
            if not method.is_static():
                argsc += 1

            print "   Stack=%i, Locals=%i, Args_size=%i" % \
                (code.max_stack, code.max_locals, argsc)

        for line in code.disassemble():
            opname = opcodes.get_opname_by_code(line[1])
            args = line[2]
            if args:
                args = ", ".join(str(arg) for arg in args)
                print "   %i:\t%s\t%s" % (line[0], opname, args)
            else:
                print "   %i:\t%s" % (line[0], opname)

        exps = code.exceptions
        if exps:
            print "  Exception table:"
            print "   from\tto\ttarget\ttype"
            for e in exps:
                ctype = e.pretty_catch_type()
                print "  % 4i\t% 4i\t% 4i\t%s" % \
                    (e.start_pc, e.end_pc, e.handler_pc, ctype)

    if options.verbose:
        if method.is_deprecated():
            print "  Deprecated: true"

        if method.is_synthetic():
            print "  Synthetic: true"

        if method.is_bridge():
            print "  Bridge: true"

        if method.is_varargs():
            print "  Varargs: true"

    if options.lines and code:
        lnt = method.get_code().get_linenumbertable()
        if lnt:
            print "  LineNumberTable:"
            for (o,l) in lnt:
                print "   line %i: %i" % (l,o)

    if options.locals and code:
        if method.cpool:
            cval = method.cpool.deref_const
        else:
            cval = str

        lvt = method.get_code().get_localvariabletable()
        lvtt = method.get_code().get_localvariabletypetable()

        if lvt:
            print "  LocalVariableTable:"
            print "   Start  Length  Slot\tName\tDescriptor"
            for (o,l,n,d,i) in lvt:
                line = (str(o), str(l), str(i), cval(n), cval(d))
                print "   %s" % "\t".join(line)

        if lvtt:
            print "  LocalVariableTypeTable:"
            print "   Start  Length  Slot\tName\tSignature"
            for (o,l,n,s,i) in lvtt:
                line = (str(o), str(l), str(i), cval(n), cval(s))
                print "   %s" % "\t".join(line)


    if options.verbose:
        exps = method.pretty_exceptions()
        if exps:
            print "  Exceptions:"
            for e in exps:
                print "   throws", e

        print



def cli_class_provides(options, info):
    print "class %s provides:" % info.pretty_this()

    for provided in sorted(info.get_provides(options.api_ignore)):
        print " ", provided
    print



def cli_class_requires(options, info):
    print "class %s requires:" % info.pretty_this()

    for required in sorted(info.get_requires(options.api_ignore)):
        print " ", required
    print



def cli_print_classinfo(options, info):
    from javaclass import platform_from_version

    if options.class_provides or options.class_requires:
        if options.class_provides:
            cli_class_provides(options, info)
        if options.class_requires:
            cli_class_requires(options, info)
        return

    sourcefile = info.get_sourcefile()
    if sourcefile:
        print "Compiled from \"%s\"" % sourcefile

    print info.pretty_descriptor(),

    if options.verbose or options.show == HEADER:
        print
        if info.get_sourcefile():
            print "  SourceFile: \"%s\"" % info.get_sourcefile()
        if info.get_signature():
            print "  Signature:", info.get_signature()
        if info.get_enclosingmethod():
            print "  EnclosingMethod:", info.get_enclosingmethod()
        major, minor = info.get_version()
        print "  minor version:", major
        print "  major version:", minor
        platform = platform_from_version(*info.version) or "unknown"
        print "  Platform:", platform

    if options.constpool:
        print "  Constants pool:"

        # we don't use the info.pretty_constants() generator here
        # because we actually want numbers for the entries, and that
        # generator skips them.
        cpool = info.cpool

        for i in xrange(1, len(cpool.consts)):
            t,v = cpool.pretty_const(i)
            if t:
                # skipping the None consts, which would be the entries
                # comprising the second half of a long or double value
                print "const #%i = %s\t%s;" % (i,t,v)
        print
        
    if options.show == HEADER:
        return

    print "{"

    for field in info.fields:
        if should_show(options, field):
            print_field(options, field)

    for method in info.methods:
        if should_show(options, method):
            print_method(options, method)

    print "}"
    print

    return 0



def cli_print_class(options, classfile):
    from javaclass import unpack_classfile

    info = unpack_classfile(classfile)
    return cli_print_classinfo(options, info)



def cli_simplify_field(options, field, data=None):
    if data is None:
        data = dict()

    data["name"] = field.get_name()
    data["type"] = field.pretty_type()
    data["access_flags"] = tuple(field.pretty_access_flags())

    ifonly(data, "signature", field.get_signature())
    ifonly(data, "deprecated", field.is_deprecated())

    cv = field.get_constantvalue()
    if cv is not None:
        t,v = field.cpool.pretty_const(cv)
        if t:
            data["constant_value"] = (t,v)

    return data



def cli_simplify_method(options, method, data=None):
    if data is None:
        data = dict()

    data["name"] = method.get_name()
    data["type"] = method.pretty_type()
    data["access_flags"] = tuple(method.pretty_access_flags())
    data["arg_types"] = method.pretty_arg_types()

    ifonly(data, "signature", method.get_signature())
    ifonly(data, "deprecated", method.is_deprecated())

    return data



def cli_simplify_fields(options, info):
    fields = list()
    for field in info.fields:
        if should_show(options, field):
            fields.append(cli_simplify_field(options, field))
    return fields



def cli_simplify_methods(options, info):
    methods = list()
    for method in info.methods:
        if should_show(options, method):
            methods.append(cli_simplify_method(options, method))
    return methods



def cli_simplify_classinfo(options, info, data=None):
    from javaclass import platform_from_version

    if data is None:
        data = dict()

    if options.class_provides:
        data["class_provides"] = info.get_provides(options.api_ignore)
    if options.class_requires:
        data["class_requires"] = info.get_requires(options.api_ignore)

    data["name"] = info.pretty_this()
    data["extends"] = info.pretty_super()
    data["implements"] = tuple(info.pretty_interfaces())
    data["source_file"] = info.get_sourcefile()

    ifonly(data, "signature", info.get_signature())
    ifonly(data, "enclosing_method", info.get_enclosingmethod())

    data["version"] = info.get_version()
    data["platform"] = platform_from_version(*info.version)

    if options.constpool:
        data["constants_pool"] = tuple(info.cpool.pretty_constants())

    data["fields"] = cli_simplify_fields(options, info)
    data["methods"] = cli_simplify_methods(options, info)

    return data



def ifonly(data, key, val):
    if val:
        data[key] = val



def cli_json_class(options, classfile):
    from javaclass import unpack_classfile
    from json import dump
    from sys import stdout
    
    info = unpack_classfile(classfile)
    data = cli_simplify_classinfo(options, info)
    dump(data, stdout, sort_keys=True, indent=2)



def cli(parser, options, rest):

    if options.verbose:
        # verbose also sets all of the following options
        options.lines = True
        options.locals = True
        options.disassemble = True
        options.sigs = True
        options.constpool = True

    # just a tiny hack to mimic some indenting sun's javap will do if
    # the output is terse
    options.indent = not(options.lines or
                         options.disassemble or
                         options.sigs)

    style = cli_print_class
    if options.json:
        style = cli_json_class

    for f in rest[1:]:
        style(options, f)
        
    return 0



def classinfo_optgroup(parser):
    from optparse import OptionGroup

    g = OptionGroup(parser, "Class Info Options")

    g.add_option("--class-provides", dest="class_provides",
                 action="store_true", default=False,
                 help="API provides information at the class level")
    
    g.add_option("--class-requires", dest="class_requires",
                 action="store_true", default=False,
                 help="API requires information at the class level")

    g.add_option("--api-ignore", dest="api_ignore",
                 action="append", default=list(),
                 help="globs of packages to not print in provides"
                 " or requires modes")

    g.add_option("--header", dest="show",
                 action="store_const", default=PUBLIC, const=HEADER,
                 help="show just the class header, no members")

    g.add_option("--public", dest="show",
                 action="store_const", const=PUBLIC,
                 help="show only public members")

    g.add_option("--package", dest="show",
                 action="store_const", const=PACKAGE,
                 help="show public and protected members")

    g.add_option("--private", dest="show",
                 action="store_const", const=PRIVATE,
                 help="show all members")

    g.add_option("-l", dest="lines", action="store_true",
                 help="show the line number table")

    g.add_option("-o", dest="locals", action="store_true",
                 help="show the local variable tables")

    g.add_option("-c", dest="disassemble", action="store_true",
                 help="disassemble method code")

    g.add_option("-s", dest="sigs", action="store_true",
                 help="show internal type signatures")

    g.add_option("-p", dest="constpool", action="store_true",
                 help="show the constants pool")

    g.add_option("--verbose", dest="verbose", action="store_true",
                 help="sets -locsp options and shows stack bounds")
    
    return g



def create_optparser():
    from optparse import OptionParser

    parser = OptionParser("%prog <options> <classfiles>")

    parser.add_option_group(classinfo_optgroup(parser))

    parser.add_option("--json", action="store_true", default=False,
                      help="output JSON")

    return parser



def main(args):
    parser = create_optparser()
    return cli(parser, *parser.parse_args(args))



#
# The end.
