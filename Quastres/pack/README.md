# Пак Quastres
- `make_pack.py blocks.yml OUT` — blockstates костров, модели плит, `Quastres.yml` для `plugins/Nexo/items/`.
- `textures/` — кора: берёза и сосна (ель) из ванильного client.jar 1.21.11; пальма — джунглевая кора, осветлена и с кольцами;
  осина — берёзовая кора, зеленовато-серая без крупных пятен. `slab_*_side` — верхняя половина блока в обеих половинах.
  Генератор текстур — `nexo-blocks/slabs/make_slab_textures.py` (та же схема) + правки в сессии (см. preview.png).
- На сервере: текстуры → `Nexo/pack/assets/orsess/textures/block/`, `generated/assets/**` → `Nexo/pack/assets/**`.
