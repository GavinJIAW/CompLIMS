# -*- coding: utf-8 -*-


import operator
import re
from collections import OrderedDict
from functools import reduce

import six
from django.db import models
from django.db.models import Q, F
from django.db.models.constants import LOOKUP_SEP
from django_filters import utils, FilterSet
from django_filters.constants import ALL_FIELDS
from django_filters.filters import CharFilter, DateTimeFromToRangeFilter
from django_filters.rest_framework import DjangoFilterBackend
from django_filters.utils import get_model_field
from rest_framework.filters import BaseFilterBackend
from django_filters.conf import settings
from coreadmin.system.models import Dept
from coreadmin.utils.models import CoreModel

class CoreModelFilterBankend(BaseFilterBackend):
    """
    自定义时间范围过滤器
    """
    def filter_queryset(self, request, queryset, view):
        create_datetime_after = request.query_params.get('create_datetime_after', None)
        create_datetime_before = request.query_params.get('create_datetime_before', None)
        update_datetime_after = request.query_params.get('update_datetime_after', None)
        update_datetime_before = request.query_params.get('update_datetime_before', None)
        if any([create_datetime_after, create_datetime_before, update_datetime_after, update_datetime_before]):
            create_filter = Q()
            if create_datetime_after and create_datetime_before:
                create_filter &= Q(create_datetime__gte=create_datetime_after) & Q(create_datetime__lte=f'{create_datetime_before} 23:59:59')
            elif create_datetime_after:
                create_filter &= Q(create_datetime__gte=create_datetime_after)
            elif create_datetime_before:
                create_filter &= Q(create_datetime__lte=f'{create_datetime_before} 23:59:59')

            # 更新时间范围过滤条件
            update_filter = Q()
            if update_datetime_after and update_datetime_before:
                update_filter &= Q(update_datetime__gte=update_datetime_after) & Q(update_datetime__lte=update_datetime_before)
            elif update_datetime_after:
                update_filter &= Q(update_datetime__gte=update_datetime_after)
            elif update_datetime_before:
                update_filter &= Q(update_datetime__lte=update_datetime_before)
            # 结合两个时间范围过滤条件
            queryset = queryset.filter(create_filter & update_filter)
            return queryset
        return queryset

def get_dept(dept_id: int, dept_all_list=None, dept_list=None):
    """
    递归获取部门的所有下级部门
    :param dept_id: 需要获取的部门id
    :param dept_all_list: 所有部门列表
    :param dept_list: 递归部门list
    :return:
    """
    if not dept_all_list:
        dept_all_list = Dept.objects.all().values("id", "parent")
    if dept_list is None:
        dept_list = [dept_id]
    for ele in dept_all_list:
        if ele.get("parent") == dept_id:
            dept_list.append(ele.get("id"))
            get_dept(ele.get("id"), dept_all_list, dept_list)
    return list(set(dept_list))


class DataLevelPermissionsFilter(BaseFilterBackend):
    """Compatibility adapter: never resolve URL patterns or whitelist rows."""
    def filter_queryset(self, request, queryset, view):
        from coreadmin.access.context import context_for
        return context_for(request, view).scope(queryset)


class CustomDjangoFilterBackend(DjangoFilterBackend):
    lookup_prefixes = {
        "^": "istartswith",
        "=": "iexact",
        "@": "search",
        "$": "iregex",
        "~": "icontains",
    }
    filter_fields = "__all__"

    def construct_search(self, field_name, lookup_expr=None):
        lookup = self.lookup_prefixes.get(field_name[0])
        if lookup:
            field_name = field_name[1:]
        else:
            lookup = lookup_expr
        if lookup:
            if field_name.endswith(lookup):
                return field_name
            return LOOKUP_SEP.join([field_name, lookup])
        return field_name

    def find_filter_lookups(self, orm_lookups, search_term_key):
        for lookup in orm_lookups:
            # if lookup.find(search_term_key) >= 0:
            new_lookup = LOOKUP_SEP.join(lookup.split(LOOKUP_SEP)[:-1]) if len(lookup.split(LOOKUP_SEP)) > 1 else lookup
            # 修复条件搜索错误 bug
            if new_lookup == search_term_key:
                return lookup
        return None

    def get_filterset_class(self, view, queryset=None):
        """
        Return the `FilterSet` class used to filter the queryset.
        """
        filterset_class = getattr(view, "filterset_class", None)
        filterset_fields = getattr(view, "filterset_fields", None)

        # TODO: remove assertion in 2.1
        if filterset_class is None and hasattr(view, "filter_class"):
            utils.deprecate(
                "`%s.filter_class` attribute should be renamed `filterset_class`." % view.__class__.__name__
            )
            filterset_class = getattr(view, "filter_class", None)

        # TODO: remove assertion in 2.1
        if filterset_fields is None and hasattr(view, "filter_fields"):
            utils.deprecate(
                "`%s.filter_fields` attribute should be renamed `filterset_fields`." % view.__class__.__name__
            )
            self.filter_fields = getattr(view, "filter_fields", None)
            if isinstance(self.filter_fields, (list, tuple)):
                filterset_fields = [
                    field[1:] if field[0] in self.lookup_prefixes.keys() else field for field in self.filter_fields
                ]
            else:
                filterset_fields = self.filter_fields

        if filterset_class:
            filterset_model = filterset_class._meta.model

            # FilterSets do not need to specify a Meta class
            if filterset_model and queryset is not None:
                assert issubclass(
                    queryset.model, filterset_model
                ), "FilterSet model %s does not match queryset model %s" % (
                    filterset_model,
                    queryset.model,
                )

            return filterset_class

        if filterset_fields and queryset is not None:
            MetaBase = getattr(self.filterset_base, "Meta", object)

            class AutoFilterSet(self.filterset_base):
                @classmethod
                def get_all_model_fields(cls, model):
                    opts = model._meta

                    return [
                        f.name
                        for f in sorted(opts.fields + opts.many_to_many)
                        if (f.name == "id")
                        or not isinstance(f, models.AutoField)
                        and not (getattr(f.remote_field, "parent_link", False))
                    ]

                @classmethod
                def get_fields(cls):
                    """
                    Resolve the 'fields' argument that should be used for generating filters on the
                    filterset. This is 'Meta.fields' sans the fields in 'Meta.exclude'.
                    """
                    model = cls._meta.model
                    fields = cls._meta.fields
                    exclude = cls._meta.exclude

                    assert not (fields is None and exclude is None), (
                        "Setting 'Meta.model' without either 'Meta.fields' or 'Meta.exclude' "
                        "has been deprecated since 0.15.0 and is now disallowed. Add an explicit "
                        "'Meta.fields' or 'Meta.exclude' to the %s class." % cls.__name__
                    )

                    # Setting exclude with no fields implies all other fields.
                    if exclude is not None and fields is None:
                        fields = ALL_FIELDS

                    # Resolve ALL_FIELDS into all fields for the filterset's model.
                    if fields == ALL_FIELDS:
                        fields = cls.get_all_model_fields(model)

                    # Remove excluded fields
                    exclude = exclude or []
                    if not isinstance(fields, dict):
                        fields = [(f, [settings.DEFAULT_LOOKUP_EXPR]) for f in fields if f not in exclude]
                    else:
                        fields = [(f, lookups) for f, lookups in fields.items() if f not in exclude]

                    return OrderedDict(fields)

                @classmethod
                def get_filters(cls):
                    """
                    Get all filters for the filterset. This is the combination of declared and
                    generated filters.
                    """

                    # No model specified - skip filter generation
                    if not cls._meta.model:
                        return cls.declared_filters.copy()

                    # Determine the filters that should be included on the filterset.
                    filters = OrderedDict()
                    fields = cls.get_fields()
                    undefined = []

                    for field_name, lookups in fields.items():
                        field = get_model_field(cls._meta.model, field_name)
                        from django.db import models
                        from timezone_field import TimeZoneField

                        # 不进行 过滤的model 类
                        if isinstance(field, (models.JSONField, TimeZoneField, models.FileField)):
                            continue
                        # warn if the field doesn't exist.
                        if field is None:
                            undefined.append(field_name)
                        # 更新默认字符串搜索为模糊搜索
                        if (
                            isinstance(field, (models.CharField))
                            and filterset_fields == "__all__"
                            and lookups == ["exact"]
                        ):
                            lookups = ["icontains"]
                        for lookup_expr in lookups:
                            filter_name = cls.get_filter_name(field_name, lookup_expr)

                            # If the filter is explicitly declared on the class, skip generation
                            if filter_name in cls.declared_filters:
                                filters[filter_name] = cls.declared_filters[filter_name]
                                continue

                            if field is not None:
                                filters[filter_name] = cls.filter_for_field(field, field_name, lookup_expr)

                    # Allow Meta.fields to contain declared filters *only* when a list/tuple
                    if isinstance(cls._meta.fields, (list, tuple)):
                        undefined = [f for f in undefined if f not in cls.declared_filters]

                    if undefined:
                        raise TypeError(
                            "'Meta.fields' must not contain non-model field names: %s" % ", ".join(undefined)
                        )

                    # Add in declared filters. This is necessary since we don't enforce adding
                    # declared filters to the 'Meta.fields' option
                    filters.update(cls.declared_filters)
                    return filters

                class Meta(MetaBase):
                    model = queryset.model
                    fields = filterset_fields

            return AutoFilterSet

        return None

    def filter_queryset(self, request, queryset, view):
        filterset = self.get_filterset(request, queryset, view)
        if filterset is None:
            return queryset
        if filterset.__class__.__name__ == "AutoFilterSet":
            queryset = filterset.queryset
            filter_fields = filterset.filters if self.filter_fields == "__all__" else self.filter_fields
            orm_lookup_dict = dict(
                zip(
                    [field for field in filter_fields],
                    [filterset.filters[lookup].lookup_expr for lookup in filterset.filters.keys()],
                )
            )
            orm_lookups = [
                self.construct_search(lookup, lookup_expr) for lookup, lookup_expr in orm_lookup_dict.items()
            ]
            conditions = []
            queries = []
            for search_term_key in filterset.data.keys():
                if (search_term_key == 'dept' and getattr(view, 'access_context', None)
                        and view.access_context.action.code == 'user.list'
                        and request.query_params.get('show_all') == '1'):
                    continue  # The authorized User list already applied the descendant business filter.
                orm_lookup = self.find_filter_lookups(orm_lookups, search_term_key)
                if not orm_lookup or filterset.data.get(search_term_key) == '':
                    continue
                filterset_data_len = len(filterset.data.getlist(search_term_key))
                if filterset_data_len == 1:
                    query = Q(**{orm_lookup: filterset.data[search_term_key]})
                    queries.append(query)
                elif filterset_data_len == 2:
                    orm_lookup += '__range'
                    query = Q(**{orm_lookup: filterset.data.getlist(search_term_key)})
                    queries.append(query)
            if len(queries) > 0:
                conditions.append(reduce(operator.and_, queries))
                queryset = queryset.filter(reduce(operator.and_, conditions))
                return queryset
            else:
                return queryset

        if not filterset.is_valid() and self.raise_exception:
            raise utils.translate_validation(filterset.errors)
        return filterset.qs
