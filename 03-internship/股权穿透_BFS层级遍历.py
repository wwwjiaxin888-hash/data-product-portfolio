"""从运行者提供的根节点和关系数据生成分层路径，支持分页读取和断点恢复。"""
import argparse
from collections import deque
import json
import math
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd


def fetch_all_subsidiaries(fetch_page, company_name, page_size=50):
    """抓全部分页"""
    all_items = []
    first_list, total = fetch_page(company_name, 1, page_size)
    all_items.extend(first_list)
    if total <= page_size:
        return all_items

    total_pages = math.ceil(total / page_size)
    print(f"    └ {company_name}: total={total}, 共 {total_pages} 页")

    for page in range(2, total_pages + 1):
        page_list, _ = fetch_page(company_name, page, page_size)
        all_items.extend(page_list)
    return all_items


def to_record(sub, level, path_list):
    return {
        'level': level,
        'path': ' > '.join(path_list),
        'name': sub.get('name'),
        'status': sub.get('status'),
    }


class CheckpointDriller:
    def __init__(self, root_company, fetch_page, output_csv, progress_file,
                 max_depth=4, page_size=50):
        self.root = root_company
        self.max_depth = max_depth
        self.page_size = page_size
        self.fetch_page = fetch_page

        self.output_csv = Path(output_csv).resolve()
        self.progress_file = Path(progress_file).resolve()

        self.visited = set()
        self.queue = deque()
        self.csv_initialized = False

        self._load_state()

    def _load_state(self):
        if not self.progress_file.exists():
            self.queue.append((self.root, 1, [self.root]))
            self._save_state()
            return

        state = json.loads(self.progress_file.read_text(encoding='utf-8'))
        if (state['root'], state['max_depth'], state['output']) != (
            self.root, self.max_depth, str(self.output_csv)
        ):
            raise ValueError("续跑需要沿用原根企业、深度和 CSV 路径。")
        committed_size = state['output_size']
        output_size = self.output_csv.stat().st_size if self.output_csv.exists() else 0
        if committed_size < 0 or output_size < committed_size:
            raise ValueError("CSV 缺失或短于断点记录，无法恢复。")
        if output_size > committed_size:
            with self.output_csv.open('r+b') as output:
                output.truncate(committed_size)
        self.csv_initialized = committed_size > 0
        self.visited = set(state['visited'])
        self.queue = deque(tuple(item) for item in state['queue'])
        print(f"加载断点，队列剩余 {len(self.queue)} 个节点。")

    def _save_state(self):
        state = {
            'root': self.root,
            'max_depth': self.max_depth,
            'output': str(self.output_csv),
            'output_size': self.output_csv.stat().st_size if self.output_csv.exists() else 0,
            'visited': list(self.visited),
            'queue': list(self.queue),
        }
        with NamedTemporaryFile(
            mode='w', dir=self.progress_file.parent, encoding='utf-8', delete=False
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            try:
                json.dump(state, temporary_file, ensure_ascii=False)
                temporary_file.close()
                os.replace(temporary_path, self.progress_file)
            finally:
                temporary_path.unlink(missing_ok=True)

    def _append_records(self, records):
        if not records:
            return
        df = pd.DataFrame(records)
        if not self.csv_initialized:
            df.to_csv(self.output_csv, index=False, encoding='utf-8-sig', mode='w')
            self.csv_initialized = True
        else:
            df.to_csv(self.output_csv, index=False, encoding='utf-8-sig',
                      mode='a', header=False)

    def run(self):
        while self.queue:
            company, depth, path = self.queue.popleft()
            if company in self.visited:
                self._save_state()
                continue
            if depth > self.max_depth:
                self.visited.add(company)
                self._save_state()
                continue

            subs = fetch_all_subsidiaries(self.fetch_page, company, self.page_size)
            self.visited.add(company)
            records = []
            for sub in subs:
                sub_name = sub.get('name')
                if not sub_name:
                    continue
                sub_path = path + [sub_name]
                records.append(to_record(sub, depth, sub_path))
                if depth + 1 <= self.max_depth and sub_name not in self.visited:
                    self.queue.append((sub_name, depth + 1, sub_path))

            self._append_records(records)
            self._save_state()

        print(f"完成，结果保存在 {self.output_csv}")


def local_fetch_page(relations):
    def fetch_page(company, page, page_size):
        records = relations.get(company, [])
        start = (page - 1) * page_size
        return records[start:start + page_size], len(records)

    return fetch_page


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("relations", type=Path, help="运行者提供的下级关系 JSON 路径，替换 xxxx")
    parser.add_argument("root", help="运行者提供的根企业名称，替换 xxxx")
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--page-size", type=int, default=50)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.relations.name == "xxxx" or not args.relations.is_file():
        parser.error("请将 xxxx 替换为已获准使用的本地下级关系 JSON 路径。")
    if args.root.strip() in ("", "xxxx"):
        parser.error("请将 xxxx 替换为下级关系数据中的根企业名称。")
    if args.max_depth < 1 or args.page_size < 1:
        parser.error("深度和分页大小须为正整数")
    paths = [args.relations.resolve(), args.output.resolve(), args.checkpoint.resolve()]
    if len(set(paths)) != len(paths):
        parser.error("输入、输出和断点文件路径必须不同")
    if args.resume:
        if not args.checkpoint.is_file():
            parser.error("续跑需要已存在的断点文件")
    elif args.output.exists() or args.checkpoint.exists():
        parser.error("请为首次运行指定新的输出和断点文件路径")
    relations = json.loads(args.relations.read_text(encoding="utf-8-sig"))
    if not isinstance(relations, dict) or any(not isinstance(records, list) for records in relations.values()):
        parser.error("关系文件应为企业名称到下级记录列表的映射。")
    if args.root not in relations:
        parser.error("根企业须出现在关系文件中。")
    driller = CheckpointDriller(
        args.root, local_fetch_page(relations), args.output, args.checkpoint,
        max_depth=args.max_depth, page_size=args.page_size,
    )
    try:
        driller.run()
    except KeyboardInterrupt:
        print("运行中断，可用 --resume 从上一次写入的断点继续。")
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
