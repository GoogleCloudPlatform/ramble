# Copyright 2013-2022 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)
import os
import re
import sys

import pytest

import spack.paths
from spack.compiler import _parse_non_system_link_dirs

is_windows = sys.platform == 'win32'
if is_windows:
    drive_m = re.search(r'[A-Za-z]:', spack.paths.test_path)
    drive = drive_m.group() if drive_m else None
#: directory with sample compiler data
datadir = os.path.join(spack.paths.test_path, 'data',
                       'compiler_verbose_output')


@pytest.fixture(autouse=True)
def allow_nonexistent_paths(monkeypatch):
    # Allow nonexistent paths to be detected as part of the output
    # for testing purposes.
    monkeypatch.setattr(os.path, 'isdir', lambda x: True)


def check_link_paths(filename, paths):
    with open(os.path.join(datadir, filename)) as file:
        output = file.read()
    detected_paths = _parse_non_system_link_dirs(output)

    actual = detected_paths
    expected = paths

    missing_paths = list(x for x in expected if x not in actual)
    assert not missing_paths

    extra_paths = list(x for x in actual if x not in expected)
    assert not extra_paths

    assert actual == expected


def test_icc16_link_paths():
    if is_windows:
        check_link_paths('icc-16.0.3.txt', [
            drive + r'\usr\tce\packages\intel\intel-16.0.3\compilers_and_libraries_2016.3.210\linux\compiler\lib\intel64_lin',  # noqa
            drive + r'\usr\tce\packages\gcc\gcc-4.9.3\lib64\gcc\x86_64-unknown-linux-gnu\4.9.3',  # noqa
            drive + r'\usr\tce\packages\gcc\gcc-4.9.3\lib64'])
    else:
        check_link_paths('icc-16.0.3.txt', [
            '/usr/tce/packages/intel/intel-16.0.3/compilers_and_libraries_2016.3.210/linux/compiler/lib/intel64_lin',  # noqa
            '/usr/tce/packages/gcc/gcc-4.9.3/lib64/gcc/x86_64-unknown-linux-gnu/4.9.3',  # noqa
            '/usr/tce/packages/gcc/gcc-4.9.3/lib64'])


def test_pgi_link_paths():
    if is_windows:
        check_link_paths('pgcc-16.3.txt', [
            drive + r'\usr\tce\packages\pgi\pgi-16.3\linux86-64\16.3\lib'])
    else:
        check_link_paths('pgcc-16.3.txt', [
            '/usr/tce/packages/pgi/pgi-16.3/linux86-64/16.3/lib'])


def test_gcc7_link_paths():
    check_link_paths('gcc-7.3.1.txt', [])


def test_clang4_link_paths():
    check_link_paths('clang-4.0.1.txt', [])


def test_xl_link_paths():
    if is_windows:
        check_link_paths('xl-13.1.5.txt', [
            drive + r'\opt\ibm\xlsmp\4.1.5\lib',
            drive + r'\opt\ibm\xlmass\8.1.5\lib',
            drive + r'\opt\ibm\xlC\13.1.5\lib'])
    else:
        check_link_paths('xl-13.1.5.txt', [
            '/opt/ibm/xlsmp/4.1.5/lib',
            '/opt/ibm/xlmass/8.1.5/lib',
            '/opt/ibm/xlC/13.1.5/lib'])


def test_cce_link_paths():
    if is_windows:
        check_link_paths('cce-8.6.5.txt', [
            drive + r'\opt\gcc\6.1.0\snos\lib64',
            drive + r'\opt\cray\dmapp\default\lib64',
            drive + r'\opt\cray\pe\mpt\7.7.0\gni\mpich-cray\8.6\lib',
            drive + r'\opt\cray\pe\libsci\17.12.1\CRAY\8.6\x86_64\lib',
            drive + r'\opt\cray\rca\2.2.16-6.0.5.0_15.34__g5e09e6d.ari\lib64',
            drive + r'\opt\cray\pe\pmi\5.0.13\lib64',
            drive + r'\opt\cray\xpmem\2.2.4-6.0.5.0_4.8__g35d5e73.ari\lib64',
            drive + r'\opt\cray\dmapp\7.1.1-6.0.5.0_49.8__g1125556.ari\lib64',
            drive + r'\opt\cray\ugni\6.0.14-6.0.5.0_16.9__g19583bb.ari\lib64',
            drive + r'\opt\cray\udreg\2.3.2-6.0.5.0_13.12__ga14955a.ari\lib64',
            drive + r'\opt\cray\alps\6.5.28-6.0.5.0_18.6__g13a91b6.ari\lib64',
            drive + r'\opt\cray\pe\atp\2.1.1\libApp',
            drive + r'\opt\cray\pe\cce\8.6.5\cce\x86_64\lib',
            drive + r'\opt\cray\wlm_detect\1.3.2-6.0.5.0_3.1__g388ccd5.ari\lib64',
            drive + r'\opt\gcc\6.1.0\snos\lib\gcc\x86_64-suse-linux\6.1.0',
            drive +
            r'\opt\cray\pe\cce\8.6.5\binutils\x86_64\x86_64-unknown-linux-gnu\lib'])
    else:
        check_link_paths('cce-8.6.5.txt', [
            '/opt/gcc/6.1.0/snos/lib64',
            '/opt/cray/dmapp/default/lib64',
            '/opt/cray/pe/mpt/7.7.0/gni/mpich-cray/8.6/lib',
            '/opt/cray/pe/libsci/17.12.1/CRAY/8.6/x86_64/lib',
            '/opt/cray/rca/2.2.16-6.0.5.0_15.34__g5e09e6d.ari/lib64',
            '/opt/cray/pe/pmi/5.0.13/lib64',
            '/opt/cray/xpmem/2.2.4-6.0.5.0_4.8__g35d5e73.ari/lib64',
            '/opt/cray/dmapp/7.1.1-6.0.5.0_49.8__g1125556.ari/lib64',
            '/opt/cray/ugni/6.0.14-6.0.5.0_16.9__g19583bb.ari/lib64',
            '/opt/cray/udreg/2.3.2-6.0.5.0_13.12__ga14955a.ari/lib64',
            '/opt/cray/alps/6.5.28-6.0.5.0_18.6__g13a91b6.ari/lib64',
            '/opt/cray/pe/atp/2.1.1/libApp',
            '/opt/cray/pe/cce/8.6.5/cce/x86_64/lib',
            '/opt/cray/wlm_detect/1.3.2-6.0.5.0_3.1__g388ccd5.ari/lib64',
            '/opt/gcc/6.1.0/snos/lib/gcc/x86_64-suse-linux/6.1.0',
            '/opt/cray/pe/cce/8.6.5/binutils/x86_64/x86_64-unknown-linux-gnu/lib'])


def test_clang_apple_ld_link_paths():
    if is_windows:
        check_link_paths('clang-9.0.0-apple-ld.txt', [
            drive + r'\Applications\Xcode.app\Contents\Developer\Platforms\MacOSX.platform\Developer\SDKs\MacOSX10.13.sdk\usr\lib'])  # noqa
    else:
        check_link_paths('clang-9.0.0-apple-ld.txt', [
            '/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX10.13.sdk/usr/lib'])  # noqa


def test_nag_mixed_gcc_gnu_ld_link_paths():
    # This is a test of a mixed NAG/GCC toolchain, i.e. 'cxx' is set to g++ and
    # is used for the rpath detection. The reference compiler output is a
    # result of
    # '/path/to/gcc/bin/g++ -Wl,-v ./main.c'.
    if is_windows:
        check_link_paths('collect2-6.3.0-gnu-ld.txt', [
            drive + r'\scratch\local1\spack\opt\spack\gcc-6.3.0-haswell\gcc-6.5.0-4sdjgrs\lib\gcc\x86_64-pc-linux-gnu\6.5.0',  # noqa
            drive + r'\scratch\local1\spack\opt\spack\gcc-6.3.0-haswell\gcc-6.5.0-4sdjgrs\lib64',  # noqa
            drive + r'\scratch\local1\spack\opt\spack\gcc-6.3.0-haswell\gcc-6.5.0-4sdjgrs\lib'])  # noqa
    else:
        check_link_paths('collect2-6.3.0-gnu-ld.txt', [
            '/scratch/local1/spack/opt/spack/gcc-6.3.0-haswell/gcc-6.5.0-4sdjgrs/lib/gcc/x86_64-pc-linux-gnu/6.5.0',  # noqa
            '/scratch/local1/spack/opt/spack/gcc-6.3.0-haswell/gcc-6.5.0-4sdjgrs/lib64',  # noqa
            '/scratch/local1/spack/opt/spack/gcc-6.3.0-haswell/gcc-6.5.0-4sdjgrs/lib'])  # noqa


def test_nag_link_paths():
    # This is a test of a NAG-only toolchain, i.e. 'cc' and 'cxx' are empty,
    # and therefore 'fc' is used for the rpath detection). The reference
    # compiler output is a result of
    # 'nagfor -Wc=/path/to/gcc/bin/gcc -Wl,-v ./main.c'.
    if is_windows:
        check_link_paths('nag-6.2-gcc-6.5.0.txt', [
            drive + r'\scratch\local1\spack\opt\spack\gcc-6.3.0-haswell\gcc-6.5.0-4sdjgrs\lib\gcc\x86_64-pc-linux-gnu\6.5.0',  # noqa
            drive + r'\scratch\local1\spack\opt\spack\gcc-6.3.0-haswell\gcc-6.5.0-4sdjgrs\lib64',  # noqa
            drive + r'\scratch\local1\spack\opt\spack\gcc-6.3.0-haswell\gcc-6.5.0-4sdjgrs\lib'])  # noqa
    else:
        check_link_paths('nag-6.2-gcc-6.5.0.txt', [
            '/scratch/local1/spack/opt/spack/gcc-6.3.0-haswell/gcc-6.5.0-4sdjgrs/lib/gcc/x86_64-pc-linux-gnu/6.5.0',  # noqa
            '/scratch/local1/spack/opt/spack/gcc-6.3.0-haswell/gcc-6.5.0-4sdjgrs/lib64',  # noqa
            '/scratch/local1/spack/opt/spack/gcc-6.3.0-haswell/gcc-6.5.0-4sdjgrs/lib'])  # noqa


def test_obscure_parsing_rules():
    if is_windows:
        check_link_paths('obscure-parsing-rules.txt', [
            drive + r'\first\path',
            drive + r'\third\path'])
    else:
        check_link_paths('obscure-parsing-rules.txt', [
            '/first/path',
            '/second/path',
            '/third/path'])
