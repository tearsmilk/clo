# Бустеры Noratrum → что нужно от TakuFarmers

Модуль ZenBoosters (Noratrum) хранит личные и глобальные множители и отдаёт их статическим методом:

```java
// Noratrum в classpath (paper-plugin.yml: dependencies.server.Noratrum: {load: BEFORE, required: false, join-classpath: true})
double m = ink.hoka.zenboosters.BoostersAPI.multiplier(player.getUniqueId(), "coins");   // 1.0 — бустера нет
// без compile-зависимости — рефлексией:
Class<?> api = Class.forName("ink.hoka.zenboosters.BoostersAPI");
double m = (double) api.getMethod("multiplier", UUID.class, String.class).invoke(null, uuid, "coins");
```
`multiplier` уже учитывает личные × глобальные и потолок типа. Есть также `global(type)` (только глобальные) и `left(uuid, type)` (мс до конца).

Точки, где TakuFarmers должен применить множитель (типы):
| Тип | Где в TakuFarmers | Как |
|---|---|---|
| `coins` | продажа урожая/блюд (все места, где игроку начисляются монеты за продажу; продажа рыбы уже учтена в Noratrum) | `amount *= multiplier(uuid, "coins")` до deposit |
| `farm_xp` | начисление опыта острова/фермы (island xp) | `xp *= multiplier(uuid, "farm_xp")` |
| `crop_growth` | таймер роста культур (CropInfo.plantedAt / время до grown) и грядок | длительность роста `/= multiplier(ownerUuid, "crop_growth")` (владелец фермы, где растёт) |
| `station_speed` | CookStart (getSeconds), жёрнов, скалка, стол семян, печь/плита (CookJob) | длительность `/= multiplier(uuid, "station_speed")` для игрока, запустившего работу |

`fishing` (клёв) применяется в Noratrum сам. Если удобнее событиями — альтернативно можно добавить в TakuFarmers отменяемые/изменяемые события
`SaleEvent(uuid, amount, setAmount)`, `IslandXpGainEvent(setAmount)`, `CropGrowTimeEvent(setMillis)`, `CookStartEvent.setSeconds(int)` — тогда Noratrum
подпишется на них и умножит сам, без правок логики на стороне фермы.
