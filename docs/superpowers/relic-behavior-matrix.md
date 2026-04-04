# Relic Behavior Matrix

**Generated**: 2026-04-03
**Total relics**: 180 | **Implemented**: 10 | **Partial**: 1 | **Unresolved (placeholder)**: 169

This matrix maps every unresolved relic to its primary trigger domain and code entrypoint, guiding batch implementation per the [design spec](specs/2026-04-03-relic-full-implementation-design.md).

## Domain Legend

| Domain | Description |
|---|---|
| on_acquire | Fires once when the relic is obtained (max HP, gold, deck mods, potion slots) |
| combat_start | One-time effect at combat start (block, debuffs, draw, energy, cards into hand) |
| turn_cycle | Triggers on turn start/end, often with counters |
| play_action | Triggers on playing/discarding/exhausting cards, or counting plays per turn/combat |
| damage_resolution | Modifies damage calc, triggers on taking/dealing damage, or grants debuff immunity |
| reward_generation | Modifies post-combat card/potion/relic/gold rewards |
| shop | Modifies shop prices, stock, or behavior |
| rest_site | Modifies rest site options or healing |
| map_flow | Modifies room entry, map pathing, or encounter composition |
| complex/deferred | Requires systems not yet implemented (orbs, stances, scry, cost randomization, UI pickers) |
| flavor_only | No mechanical effect |

## Entrypoint Legend

| Short Name | Full Path |
|---|---|
| apply_reward | `src/slay_the_spire/use_cases/apply_reward.py` |
| reward_generator | `src/slay_the_spire/domain/rewards/reward_generator.py` |
| turn_flow | `src/slay_the_spire/domain/combat/turn_flow.py` |
| hooks/runtime | `src/slay_the_spire/domain/hooks/runtime.py` |
| play_card | `src/slay_the_spire/use_cases/play_card.py` |
| enter_room | `src/slay_the_spire/use_cases/enter_room.py` |
| shop_action | `src/slay_the_spire/use_cases/shop_action.py` |
| rest_action | `src/slay_the_spire/use_cases/rest_action.py` |

---

## Full Matrix (170 rows)

| # | relic_id | name | rarity | status | domain | primary entrypoint | secondary notes |
|---|---|---|---|---|---|---|---|
| 1 | strawberry | 草莓 | common | placeholder | on_acquire | apply_reward | max HP +7 |
| 2 | pear | 梨 | uncommon | placeholder | on_acquire | apply_reward | max HP +10 |
| 3 | mango | 芒果 | rare | placeholder | on_acquire | apply_reward | max HP +14 |
| 4 | leeches_waffle | 李子华夫饼 | shop | placeholder | on_acquire | apply_reward | max HP +7, heal to full |
| 5 | old_coin | 古钱币 | rare | placeholder | on_acquire | apply_reward | +300 gold on acquire |
| 6 | vajra | 金刚杵 | common | placeholder | on_acquire | apply_reward | closure target: +1 strength (permanent) |
| 7 | oddly_smooth_stone | 光滑石 | common | placeholder | on_acquire | apply_reward | closure target: +1 dexterity (permanent) |
| 8 | war_paint | 战漆 | common | placeholder | on_acquire | apply_reward | closure target: upgrade 2 random skills on acquire |
| 9 | whetstone | 磨刀石 | common | placeholder | on_acquire | apply_reward | closure target: upgrade 2 random attacks on acquire |
| 10 | omamori | 御守 | common | placeholder | on_acquire | apply_reward | negate next 2 curses; needs counter on RunState |
| 11 | potion_belt | 药带 | common | placeholder | on_acquire | apply_reward | +2 potion slots |
| 12 | darkstone_periapt | 黑石护符 | uncommon | placeholder | on_acquire | apply_reward | +6 max HP when gaining curse |
| 13 | molten_egg_2 | 熔火蛋 | uncommon | placeholder | on_acquire | apply_reward | auto-upgrade future attack cards |
| 14 | toxic_egg_2 | 毒素蛋 | uncommon | placeholder | on_acquire | apply_reward | auto-upgrade future skill cards |
| 15 | frozen_egg_2 | 冰冻蛋 | uncommon | placeholder | on_acquire | apply_reward | auto-upgrade future power cards |
| 16 | ceramic_fish | 陶瓷鱼 | common | placeholder | on_acquire | apply_reward | +9 gold when adding card to deck |
| 17 | singing_bowl | 歌唱碗 | uncommon | placeholder | on_acquire | apply_reward | +2 max HP when skipping card reward |
| 18 | empty_cage | 空鸟笼 | boss | placeholder | on_acquire | apply_reward | remove 2 cards from deck on acquire |
| 19 | astrolabe | 星盘 | boss | placeholder | on_acquire | apply_reward | transform+upgrade 3 random cards on acquire |
| 20 | pandoras_box | 潘多拉魔盒 | boss | placeholder | on_acquire | apply_reward | transform all Strikes/Defends on acquire |
| 21 | calling_bell | 召唤铃 | boss | placeholder | on_acquire | apply_reward | gain 3 relics + 1 curse on acquire |
| 22 | tiny_house | 小屋 | boss | placeholder | on_acquire | apply_reward | heal, gold, potion, upgrade 1, gain 1 card |
| 23 | cauldron | 坩埚 | shop | placeholder | on_acquire | apply_reward | gain 5 random potions on acquire |
| 24 | dollys_mirror | 多莉的镜子 | shop | placeholder | on_acquire | apply_reward | duplicate 1 card on acquire |
| 25 | anchor | 船锚 | common | placeholder | combat_start | hooks/runtime | gain 10 block at combat start |
| 26 | bag_of_marbles | 弹珠袋 | common | placeholder | combat_start | hooks/runtime | apply 1 vulnerable to all enemies |
| 27 | bag_of_preparation | 准备背包 | common | placeholder | combat_start | hooks/runtime | draw 2 extra cards at combat start |
| 28 | lantern | 灯笼 | common | placeholder | combat_start | hooks/runtime | +1 energy first turn only |
| 29 | ring_of_the_snake | 蛇之戒 | starter | placeholder | combat_start | hooks/runtime | draw 2 extra cards at combat start (starter) |
| 30 | clockwork_souvenir | 发条纪念品 | shop | placeholder | combat_start | hooks/runtime | gain 1 artifact at combat start |
| 31 | fossilized_helix | 化石螺旋 | rare | placeholder | combat_start | hooks/runtime | gain 1 buffer at combat start |
| 32 | red_mask | 红面具 | event | placeholder | combat_start | hooks/runtime | apply 1 weak to all enemies |
| 33 | gremlin_visage | 地精容貌 | event | placeholder | combat_start | hooks/runtime | player starts with 1 weak |
| 34 | mutagenic_strength | 突变力量 | event | placeholder | combat_start | hooks/runtime | +3 strength turn 1, lose 3 at turn 1 end |
| 35 | pantograph | 示差仪 | uncommon | placeholder | combat_start | hooks/runtime | heal 25 HP at boss combat start |
| 36 | sling_of_courage | 勇气弹弓 | shop | placeholder | combat_start | hooks/runtime | +2 strength at elite combat start |
| 37 | philosophers_stone | 贤者之石 | boss | placeholder | combat_start | hooks/runtime | +1 energy per turn; all enemies +1 strength |
| 38 | mark_of_pain | 苦痛印记 | boss | placeholder | combat_start | hooks/runtime | +1 energy per turn; shuffle 2 Wounds into draw pile |
| 39 | cursed_key | 诅咒钥匙 | boss | placeholder | combat_start | hooks/runtime | +1 energy per turn; curse from non-boss chests |
| 40 | slavers_collar | 奴役者项圈 | boss | placeholder | combat_start | hooks/runtime | +1 energy in elite/boss fights only |
| 41 | runic_dome | 卢恩圆顶 | boss | placeholder | combat_start | hooks/runtime | +1 energy per turn; hide enemy intents |
| 42 | sozu | 索祖之壶 | boss | placeholder | combat_start | hooks/runtime | +1 energy per turn; block potion gain |
| 43 | velvet_choker | 丝绒项圈 | boss | placeholder | combat_start | hooks/runtime | +1 energy per turn; max 6 cards per turn |
| 44 | neows_lament | 涅奥的悲恸 | event | placeholder | combat_start | enter_room | next 3 combats enemies have 1 HP; counter on RunState |
| 45 | ancient_tea_set | 古茶具 | common | placeholder | combat_start | hooks/runtime | +2 energy first turn after rest site; flag on RunState |
| 46 | ninja_scroll | 忍术卷轴 | uncommon | placeholder | combat_start | hooks/runtime | add 3 Shivs to hand at combat start (Silent) |
| 47 | enchiridion | 军略宝典 | event | placeholder | combat_start | hooks/runtime | random power card in hand at 0 cost, combat start |
| 48 | toolbox | 工具箱 | shop | placeholder | combat_start | hooks/runtime | random colorless card in hand at combat start |
| 49 | thread_and_needle | 针线 | rare | placeholder | combat_start | hooks/runtime | gain 4 plated armor at combat start |
| 50 | twisted_funnel | 扭曲漏斗 | shop | placeholder | combat_start | hooks/runtime | apply 4 poison to all enemies at combat start (Silent) |
| 51 | happy_flower | 快乐花 | common | placeholder | turn_cycle | turn_flow | +1 energy every 3 turns; counter |
| 52 | mercury_hourglass | 水银沙漏 | common | placeholder | turn_cycle | turn_flow | deal 3 damage to all enemies at turn start |
| 53 | orichalcum | 山铜 | common | placeholder | turn_cycle | turn_flow | if 0 block at turn end, gain 6 block |
| 54 | horn_cleat | 角质护具 | uncommon | placeholder | turn_cycle | turn_flow | gain 14 block at turn 2 start |
| 55 | captains_wheel | 船长之轮 | rare | placeholder | turn_cycle | turn_flow | gain 18 block at turn 3 start |
| 56 | stone_calendar | 石制日历 | rare | placeholder | turn_cycle | turn_flow | deal 52 damage to all enemies at turn 7 end |
| 57 | incense_burner | 香炉 | rare | placeholder | turn_cycle | turn_flow | gain 1 intangible every 6 turns; counter |
| 58 | brimstone | 硫磺 | shop | placeholder | turn_cycle | turn_flow | +2 strength to player and all enemies at turn start (Ironclad) |
| 59 | warped_tongs | 弯曲铁钳 | event | placeholder | turn_cycle | turn_flow | randomly upgrade 1 hand card at turn start (combat only) |
| 60 | art_of_war | 兵法 | common | placeholder | turn_cycle | turn_flow | +1 energy next turn if no attacks played this turn |
| 61 | pocketwatch | 怀表 | rare | placeholder | turn_cycle | turn_flow | draw 3 extra next turn if ≤3 cards played this turn |
| 62 | ring_of_the_serpent | 蛇之戒指 | boss | placeholder | turn_cycle | turn_flow | +1 draw per turn; replaces ring_of_the_snake (Silent) |
| 63 | snecko_eye | 蛇眼 | boss | placeholder | turn_cycle | turn_flow | +2 draw per turn; randomize hand costs each turn |
| 64 | runic_pyramid | 卢恩金字塔 | boss | placeholder | turn_cycle | turn_flow | no discard at end of turn |
| 65 | ice_cream | 冰淇淋 | rare | placeholder | turn_cycle | turn_flow | unspent energy carries over between turns |
| 66 | calipers | 铁卡尺 | rare | placeholder | turn_cycle | turn_flow | retain up to 15 block between turns |
| 67 | meat_on_the_bone | 带骨肉 | common | placeholder | turn_cycle | turn_flow | heal 12 at combat end if HP <50% |
| 68 | face_of_cleric | 牧师的脸 | event | placeholder | turn_cycle | turn_flow | +1 max HP after each combat |
| 69 | nilrys_codex | 尼利的法典 | event | placeholder | turn_cycle | turn_flow | pick 1 of 3 random cards to shuffle into draw at turn end |
| 70 | cloak_clasp | 斗篷扣 | rare | placeholder | turn_cycle | turn_flow | gain 1 block per hand card at turn end (Watcher) |
| 71 | akabeko | 赤牛 | common | placeholder | play_action | play_card | first attack each combat deals +8 damage |
| 72 | nunchaku | 双节棍 | common | placeholder | play_action | play_card | +1 energy every 10 attacks played (cross-combat counter) |
| 73 | pen_nib | 钢笔尖 | common | placeholder | play_action | play_card | double next attack every 10 attacks played |
| 74 | kunai | 苦无 | uncommon | placeholder | play_action | play_card | +1 dexterity after 3 attacks per turn |
| 75 | shuriken | 手里剑 | uncommon | placeholder | play_action | play_card | +1 strength after 3 attacks per turn |
| 76 | ornamental_fan | 装饰扇 | uncommon | placeholder | play_action | play_card | +4 block after 3 attacks per turn |
| 77 | ink_bottle | 墨水瓶 | uncommon | placeholder | play_action | play_card | draw 1 every 10 cards played (cross-combat counter) |
| 78 | letter_opener | 拆信刀 | uncommon | placeholder | play_action | play_card | deal 5 damage to all enemies after 3 skills per turn |
| 79 | bird_faced_urn | 鸟面瓮 | rare | placeholder | play_action | play_card | heal 2 each time a power is played |
| 80 | mummified_hand | 木乃伊之手 | uncommon | placeholder | play_action | play_card | reduce 1 random hand card cost to 0 when power played |
| 81 | orange_pellets | 橙色药丸 | shop | placeholder | play_action | play_card | remove all debuffs when attack+skill+power all played in turn |
| 82 | strike_dummy | 打击假人 | uncommon | placeholder | play_action | play_card | Strike cards deal +3 damage |
| 83 | necronomicon | 死灵之书 | event | placeholder | play_action | play_card | first 2+ cost attack each turn plays twice |
| 84 | duality | 二元性 | uncommon | placeholder | play_action | play_card | +1 dexterity when attack played (Watcher) |
| 85 | wrist_blade | 护腕刃 | boss | placeholder | play_action | play_card | 0-cost attacks deal +4 damage (Silent) |
| 86 | tingsha | 铜钹 | rare | placeholder | play_action | play_card | deal 3 damage to random enemy per card discarded |
| 87 | tough_bandages | 坚韧绷带 | rare | placeholder | play_action | play_card | gain 3 block per card discarded (Silent) |
| 88 | hovering_kite | 悬浮风筝 | boss | placeholder | play_action | play_card | +1 energy next turn if discarded this turn (Silent) |
| 89 | charons_ashes | 卡戎之灰 | rare | placeholder | play_action | play_card | deal 3 damage to all enemies per card exhausted |
| 90 | dead_branch | 枯枝 | rare | placeholder | play_action | play_card | add 1 random card to hand per card exhausted |
| 91 | gremlin_horn | 地精号角 | uncommon | placeholder | play_action | play_card | +1 energy +1 draw when enemy dies |
| 92 | unceasing_top | 不息陀螺 | rare | placeholder | play_action | play_card | draw 1 when hand is empty |
| 93 | strange_spoon | 奇怪的汤勺 | shop | placeholder | play_action | play_card | 50% chance exhausted card is not exhausted |
| 94 | blue_candle | 蓝蜡烛 | uncommon | placeholder | play_action | play_card | curses can be played (lose 1 HP, exhaust) |
| 95 | medical_kit | 医疗包 | shop | placeholder | play_action | play_card | status cards can be played (exhaust) |
| 96 | abacus | 算盘 | shop | placeholder | play_action | play_card | gain 6 block on shuffle |
| 97 | sundial | 日晷 | uncommon | placeholder | play_action | play_card | +2 energy every 3 shuffles |
| 98 | the_specimen | 标本 | rare | placeholder | play_action | play_card | transfer poison to random enemy on poisoned kill (Silent) |
| 99 | bronze_scales | 青铜鳞片 | common | placeholder | damage_resolution | hooks/runtime | deal 3 thorns damage when attacked |
| 100 | centennial_puzzle | 百年谜题 | common | placeholder | damage_resolution | hooks/runtime | draw 3 on first HP loss per combat |
| 101 | the_boot | 靴子 | common | placeholder | damage_resolution | hooks/runtime | attacks deal min 5 damage |
| 102 | torii | 鸟居 | rare | placeholder | damage_resolution | hooks/runtime | unblocked damage ≤5 becomes 1 |
| 103 | tungsten_rod | 钨金棒 | rare | placeholder | damage_resolution | hooks/runtime | reduce each HP loss by 1 |
| 104 | self_forming_clay | 自塑黏土 | uncommon | placeholder | damage_resolution | hooks/runtime | gain 3 block next turn start after losing HP |
| 105 | hand_drill | 手摇钻 | shop | placeholder | damage_resolution | hooks/runtime | apply 2 vulnerable when breaking enemy block |
| 106 | runic_cube | 卢恩魔方 | boss | placeholder | damage_resolution | hooks/runtime | draw 1 when losing HP (Ironclad) |
| 107 | ginger | 姜 | rare | placeholder | damage_resolution | hooks/runtime | immune to weak |
| 108 | turnip | 芜菁 | rare | placeholder | damage_resolution | hooks/runtime | immune to vulnerable |
| 109 | paper_frog | 纸蛙 | uncommon | placeholder | damage_resolution | hooks/runtime | vulnerable multiplier 75% instead of 50% |
| 110 | paper_krane | 纸鹤 | uncommon | placeholder | damage_resolution | hooks/runtime | weak reduces damage by 40% instead of 25% (Silent) |
| 111 | champion_belt | 冠军腰带 | uncommon | placeholder | damage_resolution | hooks/runtime | apply 1 weak when applying vulnerable (Ironclad) |
| 112 | snecko_skull | 异蛇头骨 | uncommon | placeholder | damage_resolution | hooks/runtime | +1 poison when applying poison (Silent) |
| 113 | red_skull | 红头骨 | uncommon | placeholder | damage_resolution | hooks/runtime | +3 strength when HP <50% |
| 114 | duvu_doll | 杜符娃娃 | rare | placeholder | damage_resolution | hooks/runtime | +1 strength per curse in deck |
| 115 | lizard_tail | 蜥蜴尾巴 | rare | placeholder | damage_resolution | hooks/runtime | prevent death once, heal to 50% max HP |
| 116 | odd_mushroom | 奇异蘑菇 | event | placeholder | damage_resolution | hooks/runtime | vulnerable damage increase 25% instead of 50% (on self) |
| 117 | magic_flower | 魔法花 | rare | placeholder | damage_resolution | hooks/runtime | all healing +50% (Ironclad) |
| 118 | mark_of_the_bloom | 花开烙印 | event | placeholder | damage_resolution | hooks/runtime | cannot heal |
| 119 | question_card | 问号卡 | uncommon | placeholder | reward_generation | reward_generator | +1 card in card reward |
| 120 | prayer_wheel | 法轮 | rare | placeholder | reward_generation | reward_generator | +1 card in normal combat card reward |
| 121 | white_beast_statue | 白兽雕像 | uncommon | placeholder | reward_generation | reward_generator | combat reward always includes potion |
| 122 | nloths_gift | 恩洛斯的礼物 | event | placeholder | reward_generation | reward_generator | 3x rare card chance in rewards |
| 123 | black_star | 黑星 | boss | placeholder | reward_generation | reward_generator | elite drops +1 relic |
| 124 | busted_crown | 破碎王冠 | boss | partial | reward_generation | reward_generator | energy +1 already works; card reward −2 not yet |
| 125 | membership_card | 会员卡 | shop | placeholder | shop | shop_action | all shop prices 50% off |
| 126 | the_courier | 送货员 | uncommon | placeholder | shop | shop_action | shop never sells out; 20% discount |
| 127 | smiling_mask | 微笑面具 | common | placeholder | shop | shop_action | card removal always costs 50 gold |
| 128 | meal_ticket | 餐券 | common | placeholder | shop | enter_room | heal 15 on shop entry |
| 129 | maw_bank | 大嘴储蓄罐 | common | placeholder | shop | enter_room | +12 gold per room until shop entry |
| 130 | dream_catcher | 捕梦网 | common | placeholder | rest_site | rest_action | card reward after resting |
| 131 | regal_pillow | 豪华枕头 | common | placeholder | rest_site | rest_action | +15 HP when resting |
| 132 | eternal_feather | 永恒羽毛 | uncommon | placeholder | rest_site | rest_action | +3 HP per 5 cards in deck when resting |
| 133 | girya | 臂力壶铃 | rare | placeholder | rest_site | rest_action | lift option: +1 strength (max 3 uses) |
| 134 | peace_pipe | 和平烟斗 | rare | placeholder | rest_site | rest_action | toke option: remove 1 card |
| 135 | shovel | 铲子 | rare | placeholder | rest_site | rest_action | dig option: gain 1 relic |
| 136 | juzu_bracelet | 念珠 | common | placeholder | map_flow | enter_room | ? rooms can't be monster events |
| 137 | tiny_chest | 小宝箱 | common | placeholder | map_flow | enter_room | every 4th ? room grants treasure |
| 138 | matryoshka | 套娃 | uncommon | placeholder | map_flow | enter_room | next 2 normal chests give +1 relic |
| 139 | preserved_insect | 标本昆虫 | common | placeholder | map_flow | enter_room | elite enemies −25% HP |
| 140 | ssserpent_head | 蛇的头 | event | placeholder | map_flow | enter_room | +50 gold on ? room entry |
| 141 | wing_boots | 羽翼战靴 | rare | placeholder | map_flow | enter_room | ignore pathing 3 times |
| 142 | bloody_idol | 血神像 | event | placeholder | map_flow | apply_reward | heal 5 on gold gain |
| 143 | toy_ornithopter | 玩具扑翼机 | common | placeholder | map_flow | apply_reward | heal 5 on potion use |
| 144 | data_disk | 数据磁盘 | uncommon | placeholder | complex/deferred | apply_reward | +1 focus (Defect); needs focus system |
| 145 | gold_plated_cables | 镀金线缆 | uncommon | placeholder | complex/deferred | turn_flow | rightmost orb triggers extra (Defect); needs orb system |
| 146 | symbiotic_virus | 共生病毒 | uncommon | placeholder | complex/deferred | hooks/runtime | channel 1 Dark orb at combat start (Defect); needs orb system |
| 147 | cracked_core | 破损核心 | starter | placeholder | complex/deferred | hooks/runtime | channel 1 Lightning orb at combat start (Defect); needs orb system |
| 148 | frozen_core | 冰冻核心 | boss | placeholder | complex/deferred | turn_flow | channel 1 Lightning if no orbs at turn end (Defect); needs orb system |
| 149 | nuclear_battery | 核电池 | boss | placeholder | complex/deferred | hooks/runtime | channel 1 Plasma orb at combat start (Defect); needs orb system |
| 150 | runic_capacitor | 符文电容器 | shop | placeholder | complex/deferred | hooks/runtime | +3 orb slots at combat start; needs orb system |
| 151 | inserter | 插入器 | boss | placeholder | complex/deferred | turn_flow | +1 orb slot every 2 turns (Defect); needs orb system |
| 152 | emotion_chip | 情绪芯片 | rare | placeholder | complex/deferred | hooks/runtime | trigger leftmost orb on HP loss (Defect); needs orb system |
| 153 | damaru | 手摇鼓 | common | placeholder | complex/deferred | turn_flow | +1 mantra at turn start (Watcher); needs mantra/stance system |
| 154 | teardrop_locket | 泪滴吊坠 | uncommon | placeholder | complex/deferred | hooks/runtime | enter Calm at combat start (Watcher); needs stance system |
| 155 | violet_lotus | 紫莲花 | boss | placeholder | complex/deferred | hooks/runtime | +1 energy on leaving Calm (Watcher); needs stance system |
| 156 | golden_eye | 金眼 | uncommon | placeholder | complex/deferred | hooks/runtime | scry +2 cards (Watcher); needs scry system |
| 157 | melange | 美琅脂 | shop | placeholder | complex/deferred | hooks/runtime | scry 3 on shuffle (Watcher); needs scry system |
| 158 | holy_water | 圣水 | boss | placeholder | complex/deferred | hooks/runtime | add 3 upgraded Miracles at combat start (Watcher); needs Miracle card |
| 159 | pure_water | 净水 | starter | placeholder | complex/deferred | hooks/runtime | add 3 Miracles at combat start (Watcher); needs Miracle card |
| 160 | chemical_x | X 化学物 | shop | placeholder | complex/deferred | play_card | X-cost cards treat X as +2; needs X-cost support |
| 161 | sacred_bark | 圣树皮 | boss | placeholder | complex/deferred | hooks/runtime | deferred: needs potion-effect system |
| 162 | bottled_flame | 瓶装火焰 | uncommon | placeholder | complex/deferred | apply_reward | deferred: needs card picker UI |
| 163 | bottled_lightning | 瓶装闪电 | uncommon | placeholder | complex/deferred | apply_reward | deferred: needs card picker UI |
| 164 | bottled_tornado | 瓶装旋风 | uncommon | placeholder | complex/deferred | apply_reward | deferred: needs card picker UI |
| 165 | orrery | 星象仪 | shop | placeholder | complex/deferred | apply_reward | deferred: needs card picker UI |
| 166 | gambling_chip | 赌博筹码 | rare | placeholder | complex/deferred | hooks/runtime | discard any, redraw equal at combat start; needs discard picker UI |
| 167 | prismatic_shard | 虹彩碎片 | shop | placeholder | complex/deferred | reward_generator | deferred: needs multi-class card/relic pool support |
| 168 | cultist_headpiece | 邪教徒头罩 | event | placeholder | flavor_only | — | no effect (flavor) |
| 169 | spirit_poop | 灵魂便便 | event | placeholder | flavor_only | — | no effect (flavor) |
| 170 | nloths_hungry_face | 恩洛斯的饥饿脸 | event | placeholder | flavor_only | — | no effect (flavor) |

> All 170 rows correspond 1:1 to relics with `implementation_status != 'implemented'`.

---

## Domain Summary

| Domain | Count | Batch (per spec) |
|---|---|---|
| on_acquire | 24 | Batch 1 |
| combat_start | 26 | Batch 2 |
| turn_cycle | 20 | Batch 2 |
| play_action | 28 | Batch 3 |
| damage_resolution | 20 | Batch 4 |
| reward_generation | 6 | Batch 5 |
| shop | 5 | Batch 5 |
| rest_site | 6 | Batch 5 |
| map_flow | 8 | Batch 5 |
| complex/deferred | 24 | Batch 6 |
| flavor_only | 3 | — (no-op, mark implemented) |
| **Total unresolved** | **170** | |

> The 3 flavor-only relics (`cultist_headpiece`, `spirit_poop`, `nloths_hungry_face`) have no mechanical effect; they can be marked `implemented` with a trivial commit once confirmed.

---

## Cross-reference: Unresolved count verification

```
Total relics in content/relics/*.json:     180
Already implemented:                         10
Partial (busted_crown):                       1
Placeholder (unresolved):                   169
Flavor-only placeholders (no-op):             3
Mechanically unresolved:                    166
+ 1 partial needing completion:               1
= Total rows requiring implementation work: 167 + 3 flavor no-ops = 170
```

This matrix covers all 170 non-implemented relics (169 placeholder + 1 partial `busted_crown`).

> `busted_crown` is `partial` — its energy gain works but reward reduction is not yet implemented. It maps to **reward_generation** domain, batch 5.

---

## Closure Scope

The current closure pass targets four `on_acquire` relics that are mechanically straightforward and require no new subsystems:

| relic_id | status | notes |
|---|---|---|
| vajra | placeholder | closure target: +1 strength on acquire |
| oddly_smooth_stone | placeholder | closure target: +1 dexterity on acquire |
| war_paint | placeholder | closure target: upgrade 2 random skills on acquire |
| whetstone | placeholder | closure target: upgrade 2 random attacks on acquire |

The following complex relics are **intentionally left as `placeholder` or `partial`** until their required subsystems are built:

| relic_id | status | reason |
|---|---|---|
| sacred_bark | placeholder | deferred: needs potion-effect system |
| bottled_flame | placeholder | deferred: needs card picker UI |
| bottled_lightning | placeholder | deferred: needs card picker UI |
| bottled_tornado | placeholder | deferred: needs card picker UI |
| orrery | placeholder | deferred: needs card picker UI |
| prismatic_shard | placeholder | deferred: needs multi-class card/relic pool support |
