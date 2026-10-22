from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.domain_models.tags.tag import Tag
from app.services.tag_service import TagService


@pytest.fixture
def service():
    return TagService(Mock(), Mock(), Mock(), Mock())


@pytest.mark.parametrize('values', [[True], [1.5], [None], [''], ['  '], ['new', 999]])
def test_resolve_tags_validates_every_value_before_creating(service, values):
    service.tag_repo.get_tag_by_id.return_value = None
    with pytest.raises(ValueError):
        service.resolve_tags(values)
    service.tag_repo.create_tag.assert_not_called()
    service.search_engine_repo.add_tag.assert_not_called()


def test_resolve_names_strips_whitespace_and_preserves_existing_parent(service):
    tag = Tag(id=3, name='Music', parent=1)
    service.tag_repo.get_tag_by_name.return_value = tag
    assert service.resolve_tags([' Music ', 3, 'Music']) == [3]
    service.tag_repo.create_tag.assert_not_called()
    assert tag.parent == 1


def test_failed_name_creation_is_reported(service):
    service.tag_repo.get_tag_by_name.return_value = None
    service.tag_repo.create_tag.return_value = False
    with pytest.raises(ValueError, match='Could not create tag'):
        service.resolve_tags(['new'])
    service.search_engine_repo.add_tag.assert_not_called()


@pytest.mark.parametrize('operation,repository,lookup,remove', [
    ('unsave_tag', 'saved_tag_repo', 'get_saved_tag_by_user_and_tag', 'remove_saved_tag'),
    ('unblock_tag', 'blocked_tag_repo', 'get_blocked_tag_by_user_and_tag', 'remove_blocked_tag'),
])
@pytest.mark.parametrize('exists', [False, True])
def test_remove_preference_only_if_present(service, operation, repository, lookup, remove, exists):
    repo = getattr(service, repository)
    record = SimpleNamespace(user_id=1, tag_id=2) if exists else None
    getattr(repo, lookup).return_value = record
    assert getattr(service, operation)(Mock(), Tag(id=2, name='Music')) is exists
    assert getattr(repo, remove).called is exists


@pytest.mark.parametrize('operation,repository', [('save_tag', 'saved_tag_repo'), ('block_tag', 'blocked_tag_repo')])
@pytest.mark.parametrize('exists', [False, True])
def test_preference_requires_existing_tag(service, operation, repository, exists):
    service.tag_repo.get_tag_by_id.return_value = Tag(id=2, name='Music') if exists else None
    assert getattr(service, operation)(Mock(), Tag(id=2, name='Music')) is exists
    assert getattr(service, repository).create.called is exists


@pytest.mark.parametrize('operation,repository,lookup', [
    ('get_saved_tags', 'saved_tag_repo', 'get_saved_tags_by_user'),
    ('get_blocked_tags', 'blocked_tag_repo', 'get_blocked_tags_by_user'),
])
def test_preferences_are_paginated(service, operation, repository, lookup):
    getattr(getattr(service, repository), lookup).return_value = [SimpleNamespace(tag_id=i) for i in range(5)]
    service.tag_repo.get_tag_by_id.side_effect = lambda i: Tag(id=i, name=str(i))
    assert [tag.id for tag in getattr(service, operation)(Mock(), 2, 2)] == [2, 3]


def test_tag_search_and_schema_setup(service):
    service.load_schemas()
    service.search_engine_repo._ensure_ready.assert_called_once()
    assert service.query_tags('music') is service.search_engine_repo.search_with_embedding.return_value
    assert service.autocomplete('mu', 2) is service.search_engine_repo.search_by_semantic.return_value


@pytest.mark.parametrize('exists', [False, True])
def test_delete_tag(service, exists):
    tag = Tag(id=1, name='Music')
    service.tag_repo.get_tag_by_id.return_value = tag if exists else None
    assert service.delete_tag(tag) is exists
    assert service.search_engine_repo.remove_tag.called is exists
    assert service.tag_repo.remove_tag.called is exists
