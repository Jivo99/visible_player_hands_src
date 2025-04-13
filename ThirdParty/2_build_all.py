#!/usr/bin/env python3
import os, platform, subprocess, sys, re


def check_msvc_env():
    try:
        cl_out = subprocess.run('cl', capture_output=True).stderr.decode()
    except:
        print('CL compiler: not found')
        return None
    m = re.search(r'Microsoft \(R\) C\/C\+\+ Optimizing Compiler Version ([\w.]+) for (\w+)', cl_out)
    res = (m.group(1), m.group(2))
    print("CL compiler: version [%s], arch [%s]" % res)
    return res


def create_build_cmd(*, os, arch_host, build_libs, build_tdm):
    cmd = 'conan install .'

    cmd += ' -pr:b profiles/base_%s' % os
    cmd += ' -pr profiles/os_%s' % os
    cmd += ' -pr profiles/arch_%s' % arch_host
    cmd += ' -pr profiles/build_%s' % build_libs
    cmd += ' -s thedarkmod/*:build_type=%s' % build_tdm

    cmd += ' -of artefacts/%s_%s' % (os, arch_host)
    cmd += ' -d tdm_deploy'
    cmd += ' -b missing'

    return cmd


if '--bitness=64' in sys.argv[1:]:
    bitnessList = ['64']
elif '--bitness=32' in sys.argv[1:]:
    bitnessList = ['32']
else:
    bitnessList = ['64', '32']

commands = []

assert platform.machine().endswith('64'), "Use 64-bit OS for builds"
sysname = platform.system().lower()

if 'windows' in sysname:    # Windows
    assert check_msvc_env() == None, "Run build in command line without VC vars!"

    for bitness in bitnessList:
        for config in ['Release', 'Debug']:
            commands.append(create_build_cmd(
                os = 'windows',
                arch_host = bitness,
                build_libs = {'Debug': 'debugfast', 'Release': 'release'}[config],
                build_tdm = config,
            ))

else:   # Linux
    for bitness in bitnessList:
        for config in ['Release', 'Debug']:
            commands.append(create_build_cmd(
                os = 'linux',
                arch_host = bitness,
                build_libs = 'release',
                build_tdm = config,
            ))


unattended = '--unattended' in sys.argv[1:]

print("Commands to execute:")
for cmd in commands:
    print("  %s" % cmd)

if not unattended:
    yesno = input('continue? (yes/no):')
    assert yesno == 'yes', 'Cancelled by user'

for cmd in commands:
    ret = os.system(cmd)
    assert ret == 0, 'Stopped due to error for: %s' % cmd


# relativize paths in props files generated by conan
# hopefully this will be removed in future version of conan: 
#   https://github.com/conan-io/conan/issues/16427
import glob
for fn in glob.glob('artefacts/**/*.props', recursive = True):
    oldPath = os.path.abspath(os.path.dirname(fn)).replace('\\', '/')
    oldString = ('RootFolder>' + oldPath).encode()
    newString = ('RootFolder>' + '$(MSBuildThisFileDirectory)').encode()
    data = open(fn, 'rb').read()
    data = data.replace(oldString, newString)
    open(fn, 'wb').write(data)
