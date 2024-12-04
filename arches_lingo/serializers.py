from arches.app.models.models import ResourceInstance, TileModel
from arches.app.models.serializers import ArchesModelSerializer, ArchesTileSerializer


class SchemeStatementSerializer(ArchesTileSerializer):
    class Meta:
        model = TileModel
        graph_slug = "scheme"
        root_node = "statement"
        fields = "__all__"


class SchemeSerializer(ArchesModelSerializer):
    class Meta:
        model = ResourceInstance
        graph_slug = "scheme"
        nodegroups = "__all__"
        fields = "__all__"


class SchemeNamespaceSerializer(ArchesModelSerializer):
    class Meta:
        model = ResourceInstance
        graph_slug = "scheme"
        nodegroups = ["namespace"]
        fields = "__all__"


class ConceptStatementSerializer(ArchesTileSerializer):
    class Meta:
        model = TileModel
        graph_slug = "concept"
        root_node = "statement"
        fields = "__all__"


class ConceptSerializer(ArchesModelSerializer):
    class Meta:
        model = ResourceInstance
        graph_slug = "concept"
        nodegroups = "__all__"
        fields = "__all__"
