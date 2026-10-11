"""Fail closed on an interrupted shared workflow promotion at a trusted home."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat

BARRIER = 'turn-up-time-promotion.json'
BINDINGS = {'capabilities/registry.json', 'capabilities/provider-lock.json', 'provider-selection.json', 'capabilities/runtime-catalog.json'}


def installed_home(script: Path) -> Path:
    """Resolve owner-written installation identity, never a worker environment."""
    script = script.absolute()
    plain(script)
    local_home = script.parent.parent
    source = local_home.parent
    generation = source.parent
    managed = (script.parent.name == 'scripts' and local_home.name == '.claude'
               and source.name == 'source' and generation.parent.name == 'generations'
               and generation.parent.parent.name == 'turn-up-time'
               and generation.parent.parent.parent.name == 'workflows')
    if managed:
        candidate = generation / 'candidate-manifest.json'
        active = generation.parent.parent / 'install-manifest.json'
        plain(candidate)
        plain(active)
        if not candidate.is_file() or not active.is_file() or candidate.read_bytes() != active.read_bytes():
            raise ValueError('PROMOTION_INSTALL_IDENTITY_MISSING_OR_MISMATCH')
        value = json.loads(candidate.read_text(encoding='utf-8'))
        home_value = value.get('shared_claude_home')
        release = value.get('shared_release_id')
        if (not isinstance(home_value, str) or not Path(home_value).is_absolute()
                or not isinstance(release, str) or not release
                or value.get('generation') != str(generation)):
            raise ValueError('PROMOTION_INSTALL_IDENTITY_INVALID')
        for asset in (script, Path(__file__).absolute()):
            relative = asset.relative_to(source).as_posix()
            if value.get('source_inventory', {}).get(relative) != hashlib.sha256(asset.read_bytes()).hexdigest():
                raise ValueError('PROMOTION_SOURCE_IDENTITY_MISMATCH')
        home = Path(home_value)
        check(home, release)
        return home
    if (local_home / BARRIER).exists():
        check(local_home)
        return local_home
    marker = local_home / 'turn-up-time-install-manifest.json'
    if marker.is_file() and json.loads(marker.read_text(encoding='utf-8-sig')).get('state') == 'shared-release':
        raise ValueError('PROMOTION_BINDING_MISSING')
    home = Path.home() / '.claude'
    check(home)
    return home


def plain(path):
    for parent in [path, *path.parents]:
        try:
            info = parent.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('PROMOTION_REDIRECTED_PATH')


def check(home: Path, expected_release=None):
    path = home / BARRIER
    plain(path)
    if not path.exists():
        marker = home / 'turn-up-time-install-manifest.json'
        plain(marker)
        shared = marker.is_file() and json.loads(marker.read_text(encoding='utf-8-sig')).get('state') == 'shared-release'
        if expected_release or shared:
            raise ValueError('PROMOTION_BINDING_MISSING')
        return None
    if path.stat().st_size > 16384:
        raise ValueError('PROMOTION_SENTINEL_OVERSIZE')
    def unique(rows):
        result = {}
        for key, value in rows:
            if key in result:
                raise ValueError('PROMOTION_DUPLICATE_FIELD')
            result[key] = value
        return result
    value = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique)
    if (not isinstance(value, dict) or set(value) != {'schema_version', 'state', 'release_id', 'plan', 'plan_sha256', 'binding'}
            or type(value['schema_version']) is not int or value['schema_version'] != 1
            or value['state'] not in {'PREPARED', 'APPLYING', 'RECOVERY_REQUIRED', 'COMMITTED'}
            or not isinstance(value['release_id'], str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}', value['release_id'])
            or not isinstance(value['plan'], str) or not Path(value['plan']).is_absolute()
            or not isinstance(value['binding'], dict) or set(value['binding']) != BINDINGS):
        raise ValueError('PROMOTION_INVALID_SENTINEL')
    for sha in [value['plan_sha256'], *value['binding'].values()]:
        if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{64}', sha):
            raise ValueError('PROMOTION_INVALID_HASH')
    if value['state'] != 'COMMITTED':
        raise ValueError('PROMOTION_ADMISSION_PAUSED:' + value['state'])
    if expected_release and value['release_id'] != expected_release:
        raise ValueError('PROMOTION_RELEASE_MISMATCH')
    for relative, sha in value['binding'].items():
        asset = home / relative
        plain(asset)
        if not asset.is_file() or hashlib.sha256(asset.read_bytes()).hexdigest() != sha:
            raise ValueError('PROMOTION_BINDING_MISMATCH:' + relative)
    return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    args = parser.parse_args()
    try:
        check(args.home)
    except Exception as exc:
        raise SystemExit(str(exc))
