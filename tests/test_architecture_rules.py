# -*- coding: utf-8 -*-
from __future__ import absolute_import

import ast
import os
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, 'src')
PKG_DIR = os.path.join(SRC_DIR, 'dm_threemarks')
UI_DIR = os.path.join(REPO_ROOT, 'package', 'res', 'gui', 'gameface', 'mods', 'dm', 'ThreeMarks')

FORBIDDEN_DOMAIN_TOP_LEVEL = set([
    'BigWorld', 'GUI', 'Keys', 'frameworks', 'gui', 'helpers', 'skeletons',
    'PlayerEvents', 'CurrentVehicle', 'constants', 'BattleFeedbackCommon',
    'urllib2', 'os', 'threading', 'logging', 'application', 'adapters',
    'infrastructure', 'bootstrap',
])

FORBIDDEN_APP_TOP_LEVEL = set([
    'BigWorld', 'GUI', 'Keys', 'frameworks', 'gui', 'helpers', 'skeletons',
    'PlayerEvents', 'CurrentVehicle', 'constants', 'BattleFeedbackCommon',
    'urllib2', 'os', 'threading', 'adapters', 'infrastructure', 'bootstrap',
])


def _module_name_for(path):
    rel = os.path.relpath(path, SRC_DIR).replace('\\', '/')[:-3]
    parts = rel.split('/')
    if parts[-1] == '__init__':
        parts = parts[:-1]
    return '.'.join(parts)


def _layer_of(mod_name):
    parts = mod_name.split('.')
    if len(parts) >= 2 and parts[0] == 'dm_threemarks':
        return parts[1]
    return parts[0]


def _resolve_import_from(current_mod, is_pkg, node):
    level = int(getattr(node, 'level', 0) or 0)
    mod = node.module or ''
    if level == 0:
        return [mod] if mod else []
    cur_parts = current_mod.split('.')
    pkg_parts = cur_parts if is_pkg else cur_parts[:-1]
    up = level - 1
    base = pkg_parts[:max(0, len(pkg_parts) - up)]
    if mod:
        return ['.'.join(base + mod.split('.'))]
    out = []
    for alias in node.names:
        out.append('.'.join(base + [alias.name]))
    return out


class TestArchitectureRules(unittest.TestCase):

    def _iter_py_files(self):
        out = []
        for root, _dirs, files in os.walk(SRC_DIR):
            for fn in sorted(files):
                if fn.endswith('.py'):
                    out.append(os.path.join(root, fn))
        return out

    def _iter_js_files(self):
        out = []
        for root, _dirs, files in os.walk(UI_DIR):
            for fn in sorted(files):
                if fn.endswith('.js'):
                    out.append(os.path.join(root, fn))
        return out

    def test_python27_syntax_encoding_and_line_limits(self):
        entry_py = os.path.join(SRC_DIR, 'mod_three_marks.py')
        with open(entry_py, 'rb') as f:
            entry_lines = f.read().splitlines()
        self.assertLessEqual(len(entry_lines), 100, 'Entrypoint mod_three_marks.py too long: %d' % len(entry_lines))

        for path in self._iter_py_files():
            with open(path, 'rb') as f:
                raw = f.read()
            lines = raw.decode('utf-8').splitlines()
            self.assertGreaterEqual(len(lines), 1)
            self.assertIn('coding: utf-8', lines[0] + (lines[1] if len(lines) > 1 else ''), 'Missing utf-8 header: %s' % path)
            self.assertLessEqual(len(lines), 500, 'Python module exceeds 500 lines (%d): %s' % (len(lines), path))
            ast.parse(raw, path)

        for js_path in self._iter_js_files():
            with open(js_path, 'rb') as f:
                lines = f.read().decode('utf-8').splitlines()
            self.assertLessEqual(len(lines), 500, 'JS module exceeds 500 lines (%d): %s' % (len(lines), js_path))

    def test_clean_architecture_dependency_rules_and_no_cycles(self):
        py_files = self._iter_py_files()
        graph = {}
        for path in py_files:
            mod_name = _module_name_for(path)
            is_pkg = os.path.basename(path) == '__init__.py'
            layer = _layer_of(mod_name)
            with open(path, 'rb') as f:
                tree = ast.parse(f.read(), path)
            deps = set()
            for node in ast.walk(tree):
                targets = []
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        targets.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    targets.extend(_resolve_import_from(mod_name, is_pkg, node))
                for tgt in targets:
                    if not tgt:
                        continue
                    top = tgt.split('.')[0]
                    tgt_layer = _layer_of(tgt) if tgt.startswith('dm_threemarks.') else top
                    if layer == 'domain':
                        self.assertNotIn(tgt_layer, FORBIDDEN_DOMAIN_TOP_LEVEL, '%s imports forbidden %s' % (mod_name, tgt))
                    elif layer == 'application':
                        self.assertNotIn(tgt_layer, FORBIDDEN_APP_TOP_LEVEL, '%s imports forbidden %s' % (mod_name, tgt))
                    elif layer == 'adapters':
                        self.assertNotIn(tgt_layer, ('infrastructure', 'bootstrap'), '%s imports forbidden %s' % (mod_name, tgt))
                    elif layer == 'infrastructure':
                        self.assertNotIn(tgt_layer, ('bootstrap',), '%s imports forbidden %s' % (mod_name, tgt))
                    if tgt.startswith('dm_threemarks.'):
                        deps.add(tgt)
            graph[mod_name] = deps

        # DFS cycle check across module graph
        state = {}  # 0=unvisited, 1=visiting, 2=done

        def dfs(node, stack):
            st = state.get(node, 0)
            if st == 1:
                self.fail('Cycle detected: %s' % ' -> '.join(stack + [node]))
            if st == 2:
                return
            state[node] = 1
            for nxt in sorted(graph.get(node, ())):
                if nxt in graph:
                    dfs(nxt, stack + [node])
            state[node] = 2

        for m in sorted(graph):
            if state.get(m, 0) == 0:
                dfs(m, [])


if __name__ == '__main__':
    unittest.main()
