# Copyright (c) 2017 Open Source Foundries Limited.
#
# SPDX-License-Identifier: Apache-2.0

'''Sphinx extensions related to managing Zephyr applications.'''

from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.parsers.rst import directives


# TODO: extend and modify this for Windows.
#
# This could be as simple as generating a couple of sets of instructions, one
# for Unix environments, and another for Windows.
class ZephyrAppCommandsDirective(Directive):
    r'''
    This is a Zephyr directive for generating consistent documentation
    of the shell commands needed to manage (build, flash, etc.) an application.

    For example, to generate commands to build samples/hello_world for
    qemu_x86 use::

       .. zephyr-app-commands::
          :zephyr-app: samples/hello_world
          :board: qemu_x86
          :goals: build

    Directive options:

    \:tool:
      which tool to use. Valid options are currently 'cmake', 'west' and 'all'.
      The default is 'west'.

    \:app:
      path to the application to build.

    \:zephyr-app:
      path to the application to build, this is an app present in the upstream
      zephyr repository. Mutually exclusive with \:app:.

    \:cd-into:
      if set, build instructions are given from within the \:app: folder,
      instead of outside of it.

    \:generator:
      which build system to generate. Valid options are
      currently 'ninja' and 'make'. The default is 'ninja'. This option
      is not case sensitive.

    \:host-os:
      which host OS the instructions are for. Valid options are
      'unix', 'win' and 'all'. The default is 'all'.

    \:board:
      if set, the application build will target the given board.

    \:shield:
      if set, the application build will target the given shield.

    \:conf:
      if set, the application build will use the given configuration
      file.  If multiple conf files are provided, enclose the
      space-separated list of files with quotes, e.g., "a.conf b.conf".

    \:gen-args:
      if set, additional arguments to the CMake invocation

    \:build-args:
      if set, additional arguments to the build invocation

    \:build-dir:
      if set, the application build directory will *APPEND* this
      (relative, Unix-separated) path to the standard build directory. This is
      mostly useful for distinguishing builds for one application within a
      single page.

    \:goals:
      a whitespace-separated list of what to do with the app (in
      'build', 'flash', 'debug', 'debugserver', 'run'). Commands to accomplish
      these tasks will be generated in the right order.

    \:maybe-skip-config:
      if set, this indicates the reader may have already
      created a build directory and changed there, and will tweak the text to
      note that doing so again is not necessary.

    \:compact:
      if set, the generated output is a single code block with no
      additional comment lines

    '''
    has_content = False
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        'tool': directives.unchanged,
        'app': directives.unchanged,
        'zephyr-app': directives.unchanged,
        'cd-into': directives.flag,
        'generator': directives.unchanged,
        'host-os': directives.unchanged,
        'board': directives.unchanged,
        'shield': directives.unchanged,
        'conf': directives.unchanged,
        'gen-args': directives.unchanged,
        'build-args': directives.unchanged,
        'build-dir': directives.unchanged,
        'goals': directives.unchanged_required,
        'maybe-skip-config': directives.flag,
        'compact': directives.flag
    }

    TOOLS = ['cmake', 'west', 'all']
    GENERATORS = ['make', 'ninja']
    HOST_OS = ['unix', 'win', 'all']
    IN_TREE_STR = '# From the root of the zephyr repository'

    def run(self):
        # Re-run on the current document if this directive's source changes.
        self.state.document.settings.env.note_dependency(__file__)

        # Parse directive options.  Don't use os.path.sep or os.path.join here!
        # That would break if building the docs on Windows.
        tool = self.options.get('tool', 'west').lower()
        app = self.options.get('app', None)
        zephyr_app = self.options.get('zephyr-app', None)
        cd_into = 'cd-into' in self.options
        generator = self.options.get('generator', 'ninja').lower()
        host_os = self.options.get('host-os', 'all').lower()
        board = self.options.get('board', None)
        shield = self.options.get('shield', None)
        conf = self.options.get('conf', None)
        gen_args = self.options.get('gen-args', None)
        build_args = self.options.get('build-args', None)
        build_dir_append = self.options.get('build-dir', '').strip('/')
        goals = self.options.get('goals').split()
        skip_config = 'maybe-skip-config' in self.options
        compact = 'compact' in self.options

        if tool not in self.TOOLS:
            raise self.error(f'Unknown tool {tool}; choose from: {self.TOOLS}')

        if app and zephyr_app:
            raise self.error('Both app and zephyr-app options were given.')

        if generator not in self.GENERATORS:
            raise self.error(
                f'Unknown generator {generator}; choose from: {self.GENERATORS}'
            )


        if host_os not in self.HOST_OS:
            raise self.error(f'Unknown host-os {host_os}; choose from: {self.HOST_OS}')

        if compact and skip_config:
            raise self.error('Both compact and maybe-skip-config options were given.')

        app = app or zephyr_app
        in_tree = self.IN_TREE_STR if zephyr_app else None
        # Allow build directories which are nested.
        build_dir = ('build' + '/' + build_dir_append).rstrip('/')

        # Create host_os array
        host_os = [host_os] if host_os != "all" else [v for v in self.HOST_OS
                                                        if v != 'all']
        # Create tools array
        tools = [tool] if tool != "all" else [v for v in self.TOOLS
                                                if v != 'all']
        # Build the command content as a list, then convert to string.
        content = []
        tool_comment = 'Using {}:' if len(tools) > 1 else None
        run_config = {
            'host_os': host_os,
            'app': app,
            'in_tree': in_tree,
            'cd_into': cd_into,
            'board': board,
            'shield': shield,
            'conf': conf,
            'gen_args': gen_args,
            'build_args': build_args,
            'build_dir': build_dir,
            'goals': goals,
            'compact': compact,
            'skip_config': skip_config,
            'generator': generator
            }

        if 'west' in tools:
            w = self._generate_west(**run_config)
            if tool_comment:
                paragraph = nodes.paragraph()
                paragraph += nodes.Text(tool_comment.format('west'))
                content.extend((paragraph, self._lit_block(w)))
            else:
                content.extend(w)

        if 'cmake' in tools:
            c = self._generate_cmake(**run_config)
            if tool_comment:
                paragraph = nodes.paragraph()
                paragraph += nodes.Text(tool_comment.format(f'CMake and {generator}'))
                content.extend((paragraph, self._lit_block(c)))
            else:
                content.extend(c)

        if not tool_comment:
            content = [self._lit_block(content)]

        return content

    def _lit_block(self, content):
        content = '\n'.join(content)

        # Create the nodes.
        literal = nodes.literal_block(content, content)
        self.add_name(literal)
        literal['language'] = 'console'
        return literal


    def _generate_west(self, **kwargs):
        content = []
        generator = kwargs['generator']
        board = kwargs['board']
        app = kwargs['app']
        in_tree = kwargs['in_tree']
        goals = kwargs['goals']
        cd_into = kwargs['cd_into']
        build_dir = kwargs['build_dir']
        compact = kwargs['compact']
        kwargs['board'] = None
        # west always defaults to ninja
        gen_arg = ' -G\'Unix Makefiles\'' if generator == 'make' else ''
        cmake_args = gen_arg + self._cmake_args(**kwargs)
        cmake_args = f' --{cmake_args}' if cmake_args != '' else ''
        # ignore zephyr_app since west needs to run within
        # the installation. Instead rely on relative path.
        src = f' {app}' if app and not cd_into else ''
        dst = f' -d {build_dir}' if build_dir != 'build' else ''

        if in_tree and not compact:
            content.append(in_tree)

        if cd_into and app:
            content.append(f'cd {app}')

        # We always have to run west build.
        #
        # FIXME: doing this unconditionally essentially ignores the
        # maybe-skip-config option if set.
        #
        # This whole script and its users from within the
        # documentation needs to be overhauled now that we're
        # defaulting to west.
        #
        # For now, this keeps the resulting commands working.
        content.append(f'west build -b {board}{dst}{src}{cmake_args}')

        # If we're signing, we want to do that next, so that flashing
        # etc. commands can use the signed file which must be created
        # in this step.
        if 'sign' in goals:
            content.append(f'west sign{dst}')

        for goal in goals:
            if goal in {'build', 'sign'}:
                continue
            elif goal == 'flash':
                content.append(f'west flash{dst}')
            elif goal == 'debug':
                content.append(f'west debug{dst}')
            elif goal == 'debugserver':
                content.append(f'west debugserver{dst}')
            elif goal == 'attach':
                content.append(f'west attach{dst}')
            else:
                content.append(f'west build -t {goal}{dst}')

        return content

    @staticmethod
    def _mkdir(mkdir, build_dir, host_os, skip_config):
        content = []
        if skip_config:
            content.append(
                f"# If you already made a build directory ({build_dir}) and ran cmake, just 'cd {build_dir}' instead."
            )

        if host_os == 'all':
            content.append(f'mkdir {build_dir} && cd {build_dir}')
        if host_os == "unix":
            content.append(f'{mkdir} {build_dir} && cd {build_dir}')
        elif host_os == "win":
            build_dir = build_dir.replace('/', '\\')
            content.append(f'mkdir {build_dir} & cd {build_dir}')
        return content

    @staticmethod
    def _cmake_args(**kwargs):
        board = kwargs['board']
        shield = kwargs['shield']
        conf = kwargs['conf']
        gen_args = kwargs['gen_args']
        board_arg = f' -DBOARD={board}' if board else ''
        shield_arg = f' -DSHIELD={shield}' if shield else ''
        conf_arg = f' -DCONF_FILE={conf}' if conf else ''
        gen_args = f' {gen_args}' if gen_args else ''

        return f'{board_arg}{shield_arg}{conf_arg}{gen_args}'

    def _cd_into(self, mkdir, **kwargs):
        app = kwargs['app']
        host_os = kwargs['host_os']
        compact = kwargs['compact']
        build_dir = kwargs['build_dir']
        skip_config = kwargs['skip_config']
        content = []
        os_comment = None
        if len(host_os) > 1:
            os_comment = '# On {}'
            num_slashes = build_dir.count('/')
            if not app and mkdir and num_slashes == 0:
                # When there's no app and a single level deep build dir,
                # simplify output
                content.extend(self._mkdir(mkdir, build_dir, 'all',
                               skip_config))
                if not compact:
                    content.append('')
                return content
        for host in host_os:
            if host == "unix":
                if os_comment:
                    content.append(os_comment.format('Linux/macOS'))
                if app:
                    content.append(f'cd {app}')
            elif host == "win":
                if os_comment:
                    content.append(os_comment.format('Windows'))
                if app:
                    backslashified = app.replace('/', '\\')
                    content.append(f'cd {backslashified}')
            if mkdir:
                content.extend(self._mkdir(mkdir, build_dir, host, skip_config))
            if not compact:
                content.append('')
        return content

    def _generate_cmake(self, **kwargs):
        generator = kwargs['generator']
        cd_into = kwargs['cd_into']
        app = kwargs['app']
        in_tree = kwargs['in_tree']
        build_dir = kwargs['build_dir']
        build_args = kwargs['build_args']
        skip_config = kwargs['skip_config']
        goals = kwargs['goals']
        compact = kwargs['compact']

        content = []

        if in_tree and not compact:
            content.append(in_tree)

        if cd_into:
            num_slashes = build_dir.count('/')
            mkdir = 'mkdir' if num_slashes == 0 else 'mkdir -p'
            content.extend(self._cd_into(mkdir, **kwargs))
            # Prepare cmake/ninja/make variables
            source_dir = ' ' + '/'.join(['..' for _ in range(num_slashes + 1)])
            cmake_build_dir = ''
            tool_build_dir = ''
        else:
            source_dir = f' {app}' if app else ' .'
            cmake_build_dir = f' -B {build_dir}'
            tool_build_dir = f' -C {build_dir}'

        # Now generate the actual cmake and make/ninja commands
        gen_arg = ' -GNinja' if generator == 'ninja' else ''
        build_args = f' {build_args}' if build_args else ''
        cmake_args = self._cmake_args(**kwargs)

        if not compact:
            if not cd_into and skip_config:
                content.append(
                    f"# If you already ran cmake with -B{build_dir}, you can skip this step and run {generator} directly."
                )

            else:
                content.append(
                    f'# Use cmake to configure a {generator.capitalize()}-based buildsystem:'
                )


        content.append(f'cmake{cmake_build_dir}{gen_arg}{cmake_args}{source_dir}')
        if not compact:
            content.extend(['',
                            '# Now run ninja on the generated build system:'])

        if 'build' in goals:
            content.append(f'{generator}{tool_build_dir}{build_args}')
        content.extend(
            f'{generator}{tool_build_dir} {goal}'
            for goal in goals
            if goal != 'build'
        )

        return content


def setup(app):
    app.add_directive('zephyr-app-commands', ZephyrAppCommandsDirective)

    return {
        'version': '1.0',
        'parallel_read_safe': True,
        'parallel_write_safe': True
    }
