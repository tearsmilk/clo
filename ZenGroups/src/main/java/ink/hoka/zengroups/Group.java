package ink.hoka.zengroups;

import java.util.List;

/** Группа из groups.yml; perms — её собственные права из permissions.yml (без наследования). */
public record Group(String id, String display, int weight, String tabPrefix, String tabSuffix, String chatPrefix, String chatSuffix,
                    String namePrefix, String nameSuffix, List<String> inherits, List<String> perms) {}
