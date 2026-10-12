Esc-меню и экраны настроек в стиле фермы (HD, 2 px текстуры на 1 px интерфейса).

Это файлы пространства minecraft (переопределение ванильных виджетов), поэтому
в папку zenquests их положить нельзя — кладутся в корень пака Nexo:

  plugins/Nexo/pack/assets/minecraft/textures/gui/
    sprites/widget/button.png (+ .mcmeta)              — обычная кнопка
    sprites/widget/button_highlighted.png (+ .mcmeta)  — при наведении (золотой кант)
    sprites/widget/button_disabled.png (+ .mcmeta)     — неактивная
    sprites/widget/slider*.png (+ .mcmeta)             — слайдеры в настройках
    inworld_menu_background.png, inworld_menu_list_background.png,
    inworld_header_separator.png, inworld_footer_separator.png   — фоны настроек в мире
    menu_background.png, menu_list_background.png,
    header_separator.png, footer_separator.png                   — те же фоны вне мира

Установка: распаковать zip так, чтобы папка assets легла в plugins/Nexo/pack/,
затем в консоль: nexo reload all  →  tfrestart.
Само затемнение фона паузы (градиент) в ванилле текстурой не задаётся, меняются кнопки.
