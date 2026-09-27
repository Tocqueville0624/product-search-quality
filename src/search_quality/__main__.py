import argparse
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description='Local product-search quality study')
    parser.add_argument('command',choices=['download','prepare','train','evaluate'])
    parser.add_argument('--root',type=Path,default=Path.cwd())
    args=parser.parse_args()
    root=args.root.resolve()
    if args.command=='download':
        from .acquire import acquire
        acquire(root)
        return
    from .runtime import make_spark
    spark=make_spark(root)
    try:
        if args.command=='prepare':
            from .data import prepare
            result=prepare(root,spark)
        elif args.command=='train':
            from .model import train
            result=train(root,spark)
        else:
            from .model import evaluate
            result=evaluate(root,spark)
        print(json.dumps(result,indent=2,default=str))
    finally:
        spark.stop()


if __name__=='__main__':
    main()
