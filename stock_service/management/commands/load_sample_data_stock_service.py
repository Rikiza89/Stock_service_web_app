# stock_service/management/commands/load_sample_data_stock_service.py
import os
from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
from django.utils import timezone
from django.utils.translation import gettext_lazy # Changed: Removed 'as _'

# あなたのアプリケーションのモデルをインポート
# StockMovement と RefillSchedule モデルをここに含めてください
from stock_service.models import Society, User, StockObjectKind, StockObject, ObjectUser, Drawer, StockObjectDrawerPlacement, StockMovement, RefillSchedule

class Command(BaseCommand):
    """
    サンプルデータをロードするためのDjango管理コマンド。
    新しい社会、社会管理者（スーパーユーザー）、
    そしていくつかのサンプル在庫品目、オブジェクトユーザー、引き出し、
    および在庫ログ（入庫、出庫、補充）と補充スケジュールを作成します。
    """
    # Changed: Use gettext_lazy directly
    help = gettext_lazy('Loads sample data for the stock_service application, including detailed movements and refill schedules.')

    def handle(self, *args, **options):
        # Changed: Use gettext_lazy directly
        self.stdout.write(self.style.HTTP_INFO(gettext_lazy('--- サンプルデータのロードを開始します ---')))

        # --- Society Creation ---
        society_name = "1234"
        society_slug = slugify(society_name)
        superuser_username = "1234"
        superuser_password = "1234"
        superuser_email = "admin@example.com" # サンプル用のメールアドレス

        try:
            with transaction.atomic():
                # Societyを作成または取得
                society, created_society = Society.objects.get_or_create(
                    name=society_name,
                    defaults={
                        'slug': society_slug,
                        'subscription_level': 'premium', # サンプルとしてプレミアムに設定
                        'can_manage_drawers': True, # 引き出し管理を有効に
                        'shows_drawers_in_list': True, # リストに引き出し表示を有効に
                    }
                )
                if created_society:
                    # Changed: Use gettext_lazy directly
                    self.stdout.write(self.style.SUCCESS(gettext_lazy('社会 "%s" を作成しました。') % society.name))
                else:
                    # Changed: Use gettext_lazy directly
                    self.stdout.write(self.style.WARNING(gettext_lazy('社会 "%s" は既に存在します。') % society.name))
                    # 既存の社会の設定を更新（必要であれば）
                    if society.slug != society_slug:
                        society.slug = society_slug
                        society.save()
                    if society.subscription_level != 'premium':
                        society.subscription_level = 'premium'
                        society.save()
                    if not society.can_manage_drawers:
                        society.can_manage_drawers = True
                        society.save()
                    if not society.shows_drawers_in_list:
                        society.shows_drawers_in_list = True
                        society.save()


                # Superuserの作成または取得（この社会の管理者として）
                user, created_user = User.objects.get_or_create(
                    username=superuser_username,
                    society=society, # 作成した社会に紐付ける
                    defaults={
                        'email': superuser_email,
                        'is_staff': True,
                        'is_superuser': True,
                        'is_society_admin': True,
                        'is_active': True,
                    }
                )

                if created_user:
                    user.set_password(superuser_password)
                    user.save()
                    # Changed: Use gettext_lazy directly
                    self.stdout.write(self.style.SUCCESS(gettext_lazy('スーパーユーザー "%s" を作成しました。') % user.username))
                else:
                    # Changed: Use gettext_lazy directly
                    self.stdout.write(self.style.WARNING(gettext_lazy('スーパーユーザー "%s" は既に存在します。パスワードが異なる場合は手動でリセットしてください。') % user.username))
                    # パスワードを再設定（既に存在するがパスワードが違う場合に強制的に更新）
                    if not user.check_password(superuser_password):
                        user.set_password(superuser_password)
                        user.save()
                        # Changed: Use gettext_lazy directly
                        self.stdout.write(self.style.WARNING(gettext_lazy('スーパーユーザー "%s" のパスワードを更新しました。') % user.username))


                # --- Sample Stock Object Kinds ---
                # Changed: Use gettext_lazy directly
                self.stdout.write(self.style.HTTP_INFO(gettext_lazy('\n--- 在庫品目種類の作成 ---')))
                # Changed: Use gettext_lazy directly for strings
                kind1, k1_created = StockObjectKind.objects.get_or_create(society=society, name=gettext_lazy("電子部品"), defaults={'description': gettext_lazy('電子機器に使用される部品')})
                kind2, k2_created = StockObjectKind.objects.get_or_create(society=society, name=gettext_lazy("工具"), defaults={'description': gettext_lazy('作業に使用する手工具、電動工具など')})
                kind3, k3_created = StockObjectKind.objects.get_or_create(society=society, name=gettext_lazy("消耗品"), defaults={'description': gettext_lazy('定期的に消費される材料')})
                kind4, k4_created = StockObjectKind.objects.get_or_create(society=society, name=gettext_lazy("機械部品"), defaults={'description': gettext_lazy('機械の組み立てに使用される部品')})
                kind5, k5_created = StockObjectKind.objects.get_or_create(society=society, name=gettext_lazy("化学品"), defaults={'description': gettext_lazy('洗浄、接着などに使用される化学物質')})
                kind6, k6_created = StockObjectKind.objects.get_or_create(society=society, name=gettext_lazy("安全用品"), defaults={'description': gettext_lazy('作業者の安全を守るための品目')})
                kind7, k7_created = StockObjectKind.objects.get_or_create(society=society, name=gettext_lazy("原材料"), defaults={'description': gettext_lazy('製品製造の基となる未加工品')})
                kind8, k8_created = StockObjectKind.objects.get_or_create(society=society, name=gettext_lazy("事務用品"), defaults={'description': gettext_lazy('オフィスで使用する文房具など')})
                kind9, k9_created = StockObjectKind.objects.get_or_create(society=society, name=gettext_lazy("配線材料"), defaults={'description': gettext_lazy('ケーブル、コネクタなど')})
                if k1_created: self.stdout.write(self.style.SUCCESS(gettext_lazy('種類 "%s" を作成しました。') % kind1.name))
                if k2_created: self.stdout.write(self.style.SUCCESS(gettext_lazy('種類 "%s" を作成しました。') % kind2.name))
                if k3_created: self.stdout.write(self.style.SUCCESS(gettext_lazy('種類 "%s" を作成しました。') % kind3.name))
                if k4_created: self.stdout.write(self.style.SUCCESS(gettext_lazy('種類 "%s" を作成しました。') % kind4.name))
                if k5_created: self.stdout.write(self.style.SUCCESS(gettext_lazy('種類 "%s" を作成しました。') % kind5.name))
                if k6_created: self.stdout.write(self.style.SUCCESS(gettext_lazy('種類 "%s" を作成しました。') % kind6.name))
                if k7_created: self.stdout.write(self.style.SUCCESS(gettext_lazy('種類 "%s" を作成しました。') % kind7.name))
                if k8_created: self.stdout.write(self.style.SUCCESS(gettext_lazy('種類 "%s" を作成しました。') % kind8.name))
                if k9_created: self.stdout.write(self.style.SUCCESS(gettext_lazy('種類 "%s" を作成しました。') % kind9.name))


                # --- Sample Object Users ---
                # Changed: Use gettext_lazy directly
                self.stdout.write(self.style.HTTP_INFO(gettext_lazy('\n--- オブジェクトユーザーの作成 ---')))
                # Changed: Use gettext_lazy directly for strings
                obj_user1, ou1_created = ObjectUser.objects.get_or_create(society=society, name=gettext_lazy("技術部"), defaults={'contact_info': gettext_lazy('内線101'), 'notes': gettext_lazy('製品開発担当')})
                obj_user2, ou2_created = ObjectUser.objects.get_or_create(society=society, name=gettext_lazy("生産ラインA"), defaults={'contact_info': gettext_lazy('ラインリーダー'), 'notes': gettext_lazy('部品消費が最も多い')})
                obj_user3, ou3_created = ObjectUser.objects.get_or_create(society=society, name=gettext_lazy("品質管理部"), defaults={'contact_info': gettext_lazy('内線205'), 'notes': gettext_lazy('検査・評価担当')})
                obj_user4, ou4_created = ObjectUser.objects.get_or_create(society=society, name=gettext_lazy("メンテナンス部"), defaults={'contact_info': gettext_lazy('緊急連絡先'), 'notes': gettext_lazy('設備保守担当')})
                obj_user5, ou5_created = ObjectUser.objects.get_or_create(society=society, name=gettext_lazy("購買部"), defaults={'contact_info': gettext_lazy('内線300'), 'notes': gettext_lazy('在庫管理と発注')})
                obj_user6, ou6_created = ObjectUser.objects.get_or_create(society=society, name=gettext_lazy("生産ラインB"), defaults={'contact_info': gettext_lazy('Bライン担当者'), 'notes': gettext_lazy('サブ生産ライン')})
                obj_user7, ou7_created = ObjectUser.objects.get_or_create(society=society, name=gettext_lazy("研究開発部"), defaults={'contact_info': gettext_lazy('内線150'), 'notes': gettext_lazy('新規技術開発')})
                obj_user8, ou8_created = ObjectUser.objects.get_or_create(society=society, name=gettext_lazy("総務部"), defaults={'contact_info': gettext_lazy('内線400'), 'notes': gettext_lazy('オフィス運営')})
                for ou, created in [(obj_user1, ou1_created), (obj_user2, ou2_created), (obj_user3, ou3_created), (obj_user4, ou4_created), (obj_user5, ou5_created), (obj_user6, ou6_created), (obj_user7, ou7_created), (obj_user8, ou8_created)]:
                    # Changed: Use gettext_lazy directly
                    if created: self.stdout.write(self.style.SUCCESS(gettext_lazy('オブジェクトユーザー "%s" を作成しました。') % ou.name))


                # --- Helper function to create StockObject and its initial movement log ---
                def create_stock_object(
                    society_obj, name, kind_obj, initial_quantity, minimum_quantity, unit, location_description, responsible_user_obj
                ):
                    stock_item, created = StockObject.objects.get_or_create(
                        society=society_obj, name=name,
                        defaults={
                            'kind': kind_obj,
                            'current_quantity': initial_quantity, # Set initial quantity directly
                            'minimum_quantity': minimum_quantity,
                            'unit': unit,
                            'location_description': location_description
                        }
                    )
                    if created:
                        # Changed: Use gettext_lazy directly
                        self.stdout.write(self.style.SUCCESS(gettext_lazy('在庫品目 "%s" を作成しました。') % stock_item.name))
                        # Create an initial 'in' movement for historical record
                        StockMovement.objects.create(
                            society=society_obj,
                            stock_object=stock_item,
                            movement_type='in',
                            quantity=initial_quantity,
                            moved_by=responsible_user_obj,
                            # Changed: Use gettext_lazy directly
                            notes=gettext_lazy('初期在庫データ設定')
                        )
                    else:
                        self.stdout.write(self.style.WARNING(
                            # Changed: Use gettext_lazy directly
                            gettext_lazy('在庫品目 "{stock_name}" は既に存在します。').format(stock_name=stock_item.name)
                        ))
                        # If item exists and quantity differs, consider it an "adjustment" movement
                        if stock_item.current_quantity != initial_quantity:
                            old_quantity = stock_item.current_quantity
                            stock_item.current_quantity = initial_quantity
                            stock_item.save()
                            change = initial_quantity - old_quantity
                            movement_type = 'in' if change >= 0 else 'out'
                            StockMovement.objects.create(
                                society=society_obj,
                                stock_object=stock_item,
                                movement_type=movement_type,
                                quantity=abs(change),
                                moved_by=responsible_user_obj,
                                # Changed: Use gettext_lazy directly
                                notes=gettext_lazy('サンプルデータによる数量調整 (変更前: %d)') % old_quantity
                            )
                            self.stdout.write(self.style.WARNING(
                                # Changed: Use gettext_lazy directly
                                gettext_lazy('既存品目 "{stock_name}" の数量を更新しました（{old_qty} -> {new_qty}）。').format(
                                    stock_name=stock_item.name,
                                    old_qty=old_quantity,
                                    new_qty=initial_quantity
                                )
                            ))
                    return stock_item, created

                # Changed: Use gettext_lazy directly
                self.stdout.write(self.style.HTTP_INFO(gettext_lazy('\n--- サンプル在庫品目の作成 ---')))
                # Changed: Use gettext_lazy directly for strings
                stock_item1, _ = create_stock_object(society, gettext_lazy("抵抗器 10kΩ"), kind1, 500, 100, gettext_lazy('個'), gettext_lazy('棚1A'), user)
                stock_item2, _ = create_stock_object(society, gettext_lazy("ハンダごて"), kind2, 5, 2, gettext_lazy('個'), gettext_lazy('工具室'), user)
                stock_item3, _ = create_stock_object(society, gettext_lazy("単三電池"), kind3, 80, 30, gettext_lazy('本'), gettext_lazy('事務用品庫'), user)
                stock_item4, _ = create_stock_object(society, gettext_lazy("LED 赤 5mm"), kind1, 20, 50, gettext_lazy('個'), gettext_lazy('棚1A'), user) # 低在庫の例
                stock_item5, _ = create_stock_object(society, gettext_lazy("コンデンサ 0.1uF"), kind1, 300, 50, gettext_lazy('個'), gettext_lazy('棚1B'), user)
                stock_item6, _ = create_stock_object(society, gettext_lazy("デジタルマルチメータ"), kind2, 3, 1, gettext_lazy('台'), gettext_lazy('測定器棚'), user)
                stock_item7, _ = create_stock_object(society, gettext_lazy("グリス"), kind3, 15, 5, gettext_lazy('本'), gettext_lazy('消耗品棚'), user)
                stock_item8, _ = create_stock_object(society, gettext_lazy("M3 ネジ (10mm)"), kind4, 1000, 500, gettext_lazy('個'), gettext_lazy('ネジ箱A'), user)
                stock_item9, _ = create_stock_object(society, gettext_lazy("洗浄液"), kind5, 10, 3, gettext_lazy('L'), gettext_lazy('薬品庫'), user)
                stock_item10, _ = create_stock_object(society, gettext_lazy("保護メガネ"), kind6, 25, 10, gettext_lazy('個'), gettext_lazy('安全用品棚'), user)
                stock_item11, _ = create_stock_object(society, gettext_lazy("半導体チップ XYZ-001"), kind1, 5, 10, gettext_lazy('個'), gettext_lazy('クリーンルーム保管'), user) # 低在庫の例
                stock_item12, _ = create_stock_object(society, gettext_lazy("交換用ブレード (カッター)"), kind3, 10, 20, gettext_lazy('枚'), gettext_lazy('工具消耗品'), user) # 低在庫の例
                stock_item13, _ = create_stock_object(society, gettext_lazy("アルミ板 (A5サイズ)"), kind7, 50, 20, gettext_lazy('枚'), gettext_lazy('原材料倉庫'), user)
                stock_item14, _ = create_stock_object(society, gettext_lazy("ボールペン (青)"), kind8, 100, 20, gettext_lazy('本'), gettext_lazy('文具庫'), user)
                stock_item15, _ = create_stock_object(society, gettext_lazy("テスターリード"), kind2, 15, 5, gettext_lazy('セット'), gettext_lazy('測定器棚'), user)
                stock_item16, _ = create_stock_object(society, gettext_lazy("小型モーター RS-550"), kind4, 8, 10, gettext_lazy('個'), gettext_lazy('機械部品棚'), user) # 低在庫
                stock_item17, _ = create_stock_object(society, gettext_lazy("潤滑油 (500ml)"), kind5, 7, 3, gettext_lazy('本'), gettext_lazy('薬品庫'), user)
                stock_item18, _ = create_stock_object(society, gettext_lazy("静電対策リストバンド"), kind6, 30, 15, gettext_lazy('個'), gettext_lazy('安全用品棚'), user)
                stock_item19, _ = create_stock_object(society, gettext_lazy("基板 (汎用)"), kind1, 200, 80, gettext_lazy('枚'), gettext_lazy('電子部品倉庫'), user)
                stock_item20, _ = create_stock_object(society, gettext_lazy("USBケーブル (Type-A to B)"), kind3, 40, 10, gettext_lazy('本'), gettext_lazy('消耗品棚'), user)
                stock_item21, _ = create_stock_object(society, gettext_lazy("プラスドライバー (+2)"), kind2, 12, 5, gettext_lazy('本'), gettext_lazy('工具室'), user)
                stock_item22, _ = create_stock_object(society, gettext_lazy("A4コピー用紙"), kind8, 2, 5, gettext_lazy('束'), gettext_lazy('事務用品庫'), user) # 低在庫

                stock_item23, _ = create_stock_object(society, gettext_lazy("イーサネットケーブル (5m)"), kind9, 25, 10, gettext_lazy('本'), gettext_lazy('配線材料棚'), user)
                stock_item24, _ = create_stock_object(society, gettext_lazy("はんだ (Sn60Pb40)"), kind3, 5, 2, gettext_lazy('巻'), gettext_lazy('電子部品消耗品'), user)
                stock_item25, _ = create_stock_object(society, gettext_lazy("精密ピンセット"), kind2, 8, 3, gettext_lazy('本'), gettext_lazy('工具室'), user)
                stock_item26, _ = create_stock_object(society, gettext_lazy("ベアリング (608ZZ)"), kind4, 150, 50, gettext_lazy('個'), gettext_lazy('機械部品箱'), user)
                stock_item27, _ = create_stock_object(society, gettext_lazy("アセトン (1L)"), kind5, 3, 1, gettext_lazy('本'), gettext_lazy('薬品庫'), user)
                stock_item28, _ = create_stock_object(society, gettext_lazy("防塵マスク"), kind6, 50, 20, gettext_lazy('枚'), gettext_lazy('安全用品棚'), user)
                stock_item29, _ = create_stock_object(society, gettext_lazy("銅線 (φ0.5mm)"), kind7, 10, 5, gettext_lazy('巻'), gettext_lazy('原材料倉庫'), user)
                stock_item30, _ = create_stock_object(society, gettext_lazy("付箋 (75x75mm)"), kind8, 20, 5, gettext_lazy('冊'), gettext_lazy('文具庫'), user)


                # --- Sample Drawers and Placements (if society manages drawers) ---
                if society.can_manage_drawers:
                    # Changed: Use gettext_lazy directly
                    self.stdout.write(self.style.HTTP_INFO(gettext_lazy('\n--- サンプル引き出しと配置の作成 ---')))
                    # Changed: Use gettext_lazy directly for strings
                    drawer1, d1_created = Drawer.objects.get_or_create(society=society, cabinet_name=gettext_lazy("電子部品キャビネット"), drawer_letter_x='A', drawer_number_y=1, defaults={'description': gettext_lazy('抵抗器用の引き出し')})
                    drawer2, d2_created = Drawer.objects.get_or_create(society=society, cabinet_name=gettext_lazy("電子部品キャビネット"), drawer_letter_x='A', drawer_number_y=2, defaults={'description': gettext_lazy('LED用の引き出し')})
                    drawer3, d3_created = Drawer.objects.get_or_create(society=society, cabinet_name=gettext_lazy("電子部品キャビネット"), drawer_letter_x='B', drawer_number_y=1, defaults={'description': gettext_lazy('コンデンサ、ダイオードなど')} )
                    drawer4, d4_created = Drawer.objects.get_or_create(society=society, cabinet_name=gettext_lazy("消耗品キャビネット"), drawer_letter_x='A', drawer_number_y=1, defaults={'description': gettext_lazy('電池、グリスなど')})
                    drawer5, d5_created = Drawer.objects.get_or_create(society=society, cabinet_name=gettext_lazy("消耗品キャビネット"), drawer_letter_x='A', drawer_number_y=2, defaults={'description': gettext_lazy('カッター刃、テープなど')})
                    drawer6, d6_created = Drawer.objects.get_or_create(society=society, cabinet_name=gettext_lazy("工具キャビネット"), drawer_letter_x='C', drawer_number_y=1, defaults={'description': gettext_lazy('小型工具類')})
                    drawer7, d7_created = Drawer.objects.get_or_create(society=society, cabinet_name=gettext_lazy("機械部品キャビネット"), drawer_letter_x='D', drawer_number_y=1, defaults={'description': gettext_lazy('ネジ、ワッシャーなど')})
                    drawer8, d8_created = Drawer.objects.get_or_create(society=society, cabinet_name=gettext_lazy("事務用品キャビネット"), drawer_letter_x='E', drawer_number_y=1, defaults={'description': gettext_lazy('筆記用具、紙類')})
                    drawer9, d9_created = Drawer.objects.get_or_create(society=society, cabinet_name=gettext_lazy("電子部品キャビネット"), drawer_letter_x='B', drawer_number_y=2, defaults={'description': gettext_lazy('ICチップ、ソケット類')} )
                    drawer10, d10_created = Drawer.objects.get_or_create(society=society, cabinet_name=gettext_lazy("工具キャビネット"), drawer_letter_x='C', drawer_number_y=2, defaults={'description': gettext_lazy('特殊工具')} )

                    for d, created in [(drawer1, d1_created), (drawer2, d2_created), (drawer3, d3_created), (drawer4, d4_created), (drawer5, d5_created), (drawer6, d6_created), (drawer7, d7_created), (drawer8, d8_created), (drawer9, d9_created), (drawer10, d10_created)]:
                        # Changed: Use gettext_lazy directly
                        if created: self.stdout.write(self.style.SUCCESS(gettext_lazy('引き出し "%s" を作成しました。') % d.__str__()))


                    # Clear location_description for items that will be placed in drawers
                    items_to_clear_location = [
                        stock_item1, stock_item3, stock_item4, stock_item5, stock_item7, stock_item8,
                        stock_item11, stock_item12, stock_item14, stock_item19, stock_item20,
                        stock_item21, stock_item22, stock_item24, stock_item26, stock_item30,
                        stock_item25 # Added for a new placement
                    ]
                    for item in items_to_clear_location:
                        # Changed: Use gettext_lazy directly
                        StockObject.objects.filter(pk=item.pk).update(location_description=gettext_lazy(''))


                    # Helper function to create StockObjectDrawerPlacement
                    def create_placement(stock_obj, drawer_obj, quantity):
                        placement, created = StockObjectDrawerPlacement.objects.get_or_create(
                            stock_object=stock_obj, drawer=drawer_obj,
                            defaults={'quantity': quantity}
                        )
                        if created:
                            # Changed: Use gettext_lazy directly
                            self.stdout.write(self.style.SUCCESS(gettext_lazy('"{stock_name}" を引き出し "{drawer_name}" に配置しました。').format(stock_name=stock_obj.name, drawer_name=str(drawer_obj))))
                        else:
                             # If existing, update quantity if different
                            if placement.quantity != quantity:
                                self.stdout.write(self.style.WARNING(
                                    # Changed: Use gettext_lazy directly
                                    gettext_lazy('既存の配置 "{stock_name}" (引き出し "{drawer_name}") の数量を更新しました: {old_qty} -> {new_qty}').format(
                                        stock_name=stock_obj.name,
                                        drawer_name=str(drawer_obj), # Convert drawer_obj to string explicitly
                                        old_qty=placement.quantity,
                                        new_qty=quantity
                                    )
                                ))
                                placement.quantity = quantity
                                placement.save()
                        return placement, created

                    create_placement(stock_item1, drawer1, 300) # 抵抗器 10kΩ
                    create_placement(stock_item4, drawer2, 20) # LED 赤 5mm
                    create_placement(stock_item5, drawer3, 250) # コンデンサ 0.1uF
                    create_placement(stock_item3, drawer4, 70) # 単三電池
                    create_placement(stock_item7, drawer4, 10) # グリス
                    create_placement(stock_item12, drawer5, 8) # 交換用ブレード (カッター)
                    create_placement(stock_item19, drawer3, 150) # 基板 (汎用)
                    create_placement(stock_item21, drawer6, 10) # プラスドライバー (+2)
                    create_placement(stock_item8, drawer7, 800) # M3 ネジ (10mm)
                    create_placement(stock_item14, drawer8, 90) # ボールペン (青)
                    create_placement(stock_item22, drawer8, 2) # A4コピー用紙
                    create_placement(stock_item20, drawer5, 35) # USBケーブル (Type-A to B)

                    # New placements
                    create_placement(stock_item11, drawer9, 5) # 半導体チップ XYZ-001
                    create_placement(stock_item24, drawer4, 5) # はんだ (Sn60Pb40)
                    create_placement(stock_item26, drawer7, 100) # ベアリング (608ZZ)
                    create_placement(stock_item30, drawer8, 18) # 付箋 (75x75mm)
                    create_placement(stock_item25, drawer6, 8) # 精密ピンセット


                # --- StockMovement Entries (In/Out, Refilling) ---
                # Changed: Use gettext_lazy directly
                self.stdout.write(self.style.HTTP_INFO(gettext_lazy('\n--- 在庫移動ログの作成 (入庫/出庫/補充) ---')))

                # Note: 'moved_by' refers to the system 'User' (admin),
                # for the 'ObjectUser' (department/team) involved, we add a note in 'notes'.

                # --- Outgoing Movements ---
                # 技術部が抵抗器を消費
                quantity_out_1 = 20
                StockMovement.objects.create(
                    society=society,
                    stock_object=stock_item1,
                    movement_type='out',
                    quantity=quantity_out_1,
                    moved_by=user,
                    # Changed: Use gettext_lazy directly
                    notes=gettext_lazy('製品試作用 (要求元: %s)') % obj_user1.name
                )
                stock_item1.current_quantity -= quantity_out_1
                stock_item1.save()
                # Changed: Use gettext_lazy directly
                self.stdout.write(self.style.SUCCESS(gettext_lazy('ログ: "%s" から %d %s 出庫 (残: %d)') % (stock_item1.name, quantity_out_1, stock_item1.unit, stock_item1.current_quantity)))

                # 生産ラインAがLEDを消費 (低在庫品目)
                quantity_out_2 = 10
                StockMovement.objects.create(
                    society=society,
                    stock_object=stock_item4,
                    movement_type='out',
                    quantity=quantity_out_2,
                    moved_by=user,
                    # Changed: Use gettext_lazy directly
                    notes=gettext_lazy('ライン消費 (要求元: %s)') % obj_user2.name
                )
                stock_item4.current_quantity -= quantity_out_2
                stock_item4.save()
                # Changed: Use gettext_lazy directly
                self.stdout.write(self.style.SUCCESS(gettext_lazy('ログ: "%s" から %d %s 出庫 (残: %d)') % (stock_item4.name, quantity_out_2, stock_item4.unit, stock_item4.current_quantity)))

                # メンテナンス部がハンダごてを使用
                quantity_out_3 = 1
                StockMovement.objects.create(
                    society=society,
                    stock_object=stock_item2,
                    movement_type='out',
                    quantity=quantity_out_3,
                    moved_by=user,
                    # Changed: Use gettext_lazy directly
                    notes=gettext_lazy('設備修理のため一時使用 (要求元: %s)') % obj_user4.name
                )
                stock_item2.current_quantity -= quantity_out_3
                stock_item2.save()
                # Changed: Use gettext_lazy directly
                self.stdout.write(self.style.SUCCESS(gettext_lazy('ログ: "%s" から %d %s 出庫 (残: %d)') % (stock_item2.name, quantity_out_3, stock_item2.unit, stock_item2.current_quantity)))

                # 研究開発部が半導体チップを消費
                quantity_out_4 = 2
                StockMovement.objects.create(
                    society=society,
                    stock_object=stock_item11,
                    movement_type='out',
                    quantity=quantity_out_4,
                    moved_by=user,
                    # Changed: Use gettext_lazy directly
                    notes=gettext_lazy('研究開発プロジェクト用 (要求元: %s)') % obj_user7.name
                )
                stock_item11.current_quantity -= quantity_out_4
                stock_item11.save()
                # Changed: Use gettext_lazy directly
                self.stdout.write(self.style.SUCCESS(gettext_lazy('ログ: "%s" から %d %s 出庫 (残: %d)') % (stock_item11.name, quantity_out_4, stock_item11.unit, stock_item11.current_quantity)))


                # --- Refilling (Incoming 'in' movements) Logs ---
                # 抵抗器を補充
                restock_qty_resistor = 500
                StockMovement.objects.create(
                    society=society,
                    stock_object=stock_item1,
                    movement_type='in',
                    quantity=restock_qty_resistor,
                    moved_by=user,
                    # Changed: Use gettext_lazy directly
                    notes=gettext_lazy('定期発注による補充')
                )
                stock_item1.current_quantity += restock_qty_resistor
                stock_item1.save()
                # Changed: Use gettext_lazy directly
                self.stdout.write(self.style.SUCCESS(gettext_lazy('ログ: "%s" を %d %s 補充 (残: %d)') % (stock_item1.name, restock_qty_resistor, stock_item1.unit, stock_item1.current_quantity)))

                # LEDを補充 (低在庫からの回復)
                restock_qty_led = 100
                StockMovement.objects.create(
                    society=society,
                    stock_object=stock_item4,
                    movement_type='in',
                    quantity=restock_qty_led,
                    moved_by=user,
                    # Changed: Use gettext_lazy directly
                    notes=gettext_lazy('緊急発注による補充')
                )
                stock_item4.current_quantity += restock_qty_led
                stock_item4.save()
                # Changed: Use gettext_lazy directly
                self.stdout.write(self.style.SUCCESS(gettext_lazy('ログ: "%s" を %d %s 補充 (残: %d)') % (stock_item4.name, restock_qty_led, stock_item4.unit, stock_item4.current_quantity)))

                # A4コピー用紙を補充
                restock_qty_paper = 10
                StockMovement.objects.create(
                    society=society,
                    stock_object=stock_item22,
                    movement_type='in',
                    quantity=restock_qty_paper,
                    moved_by=user,
                    # Changed: Use gettext_lazy directly
                    notes=gettext_lazy('月次購入 (担当: %s)') % obj_user8.name
                )
                stock_item22.current_quantity += restock_qty_paper
                stock_item22.save()
                # Changed: Use gettext_lazy directly
                self.stdout.write(self.style.SUCCESS(gettext_lazy('ログ: "%s" を %d %s 補充 (残: %d)') % (stock_item22.name, restock_qty_paper, stock_item22.unit, stock_item22.current_quantity)))


                # --- Refill Schedule Entries (Future Incoming) ---
                # Changed: Use gettext_lazy directly
                self.stdout.write(self.style.HTTP_INFO(gettext_lazy('\n--- 補充スケジュールの作成 ---')))

                now = timezone.now()

                # 半導体チップの今後の補充予定
                future_date1 = (now + timedelta(days=7)).date()
                RefillSchedule.objects.get_or_create(
                    society=society,
                    stock_object=stock_item11,
                    scheduled_date=future_date1,
                    quantity_to_refill=50,
                    defaults={
                        # Changed: Use gettext_lazy directly
                        'notes': gettext_lazy('サプライヤーからの来週の配送予定'),
                        'is_completed': False,
                    }
                )
                # Changed: Use gettext_lazy directly
                self.stdout.write(self.style.SUCCESS(gettext_lazy('補充スケジュール: "%s" の %d %s 補充を %s に設定しました。') % (stock_item11.name, 50, stock_item11.unit, future_date1.strftime('%Y-%m-%d'))))

                # 小型モーターの定期補充
                future_date2 = (now + timedelta(days=14)).date()
                RefillSchedule.objects.get_or_create(
                    society=society,
                    stock_object=stock_item16,
                    scheduled_date=future_date2,
                    quantity_to_refill=20,
                    defaults={
                        # Changed: Use gettext_lazy directly
                        'notes': gettext_lazy('月次発注による定期補充'),
                        'is_completed': False,
                    }
                )
                # Changed: Use gettext_lazy directly
                self.stdout.write(self.style.SUCCESS(gettext_lazy('補充スケジュール: "%s" の %d %s 補充を %s に設定しました。') % (stock_item16.name, 20, stock_item16.unit, future_date2.strftime('%Y-%m-%d'))))

                # 完了済みの補充スケジュール
                past_date = (now - timedelta(days=30)).date()
                RefillSchedule.objects.get_or_create(
                    society=society,
                    stock_object=stock_item20,
                    scheduled_date=past_date,
                    quantity_to_refill=20,
                    defaults={
                        # Changed: Use gettext_lazy directly
                        'notes': gettext_lazy('先月の完了済み補充'),
                        'is_completed': True,
                        'completed_date': past_date,
                    }
                )
                # Changed: Use gettext_lazy directly
                self.stdout.write(self.style.SUCCESS(gettext_lazy('補充スケジュール: "%s" の %d %s 補充 (完了済み) を %s に設定しました。') % (stock_item20.name, 20, stock_item20.unit, past_date.strftime('%Y-%m-%d'))))

                # Changed: Use gettext_lazy directly
                self.stdout.write(self.style.WARNING(gettext_lazy('\n注意: 提供されたモデルでは、将来の「出庫」をスケジュールするための専用のモデルフィールドがありません。そのため、補充スケジュール（RefillSchedule）のみが作成されます。')))


        except Exception as e:
            # Changed: Use gettext_lazy directly
            self.stdout.write(self.style.ERROR(gettext_lazy('データのロード中にエラーが発生しました: %s') % str(e)))
            # Changed: Use gettext_lazy directly
            raise CommandError(gettext_lazy('データのロードに失敗しました。'))

        # Changed: Use gettext_lazy directly
        self.stdout.write(self.style.HTTP_INFO(gettext_lazy('\n--- サンプルデータのロードが完了しました ---')))