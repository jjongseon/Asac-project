import os
import re
import time
import requests
import pandas as pd

# 1. 칭호 세분화 파싱
def parse_badges_to_dict(badges_list):
    badge_data = {
        'is_pledge_master': False, 'is_backer': False, 
        'backer_number': None, 'is_prior_backer': False, 'is_pathfinder': False
    }
    if not badges_list: return badge_data
    for b in badges_list:
        b_type = b.get('badgeType')
        b_num = b.get('backerNumber')
        if b_type == 1: badge_data['is_pledge_master'] = True
        elif b_type == 3: badge_data['is_backer'] = True; badge_data['backer_number'] = b_num
        elif b_type == 4: badge_data['is_prior_backer'] = True
        elif b_type == 5: badge_data['is_pathfinder'] = True
    return badge_data

# 2. HTML에서 Thread ID 추출
def extract_thread_id_from_html(project_url, headers):
    target_url = project_url if project_url.endswith('/comments') else f"{project_url}/comments"
    try:
        res = requests.get(target_url, headers=headers, timeout=10)
        if res.status_code == 200:
            match = re.search(r'"commentThreadID":\s*(\d+)', res.text)
            if match: return int(match.group(1))
    except Exception as e:
        pass
    return None

# 3-1. [신규 핵심] 중첩된 모든 작성자 ID 추출 (재귀 함수)
def get_all_author_ids_recursive(items):
    author_ids = set()
    for item in items:
        if item.get('authorID') is not None:
            author_ids.add(item.get('authorID'))
        # 대댓글이 있다면 그 안의 작성자 ID도 파고들어서 추출
        children = item.get('children')
        if children:
            author_ids.update(get_all_author_ids_recursive(children))
    return list(author_ids)

# 3-2. [신규 핵심] 중첩된 댓글 데이터 병합 추출 (재귀 함수)
def extract_comments_recursive(items, user_mapping, project_name, current_depth=0, fallback_parent_id=None):
    extracted_data = []
    for item in items:
        author_id = str(item.get('authorID'))
        user_info = user_mapping.get(author_id, {})
        badges_dict = parse_badges_to_dict(user_info.get('badges', []))
        
        children_count = item.get('childrenTotalCount', 0)
        
        # 서버에서 명시한 parentID가 있으면 쓰고, 없으면 상위 함수에서 넘겨준 부모 ID 사용
        actual_parent_id = item.get('parentID') or fallback_parent_id
        current_comment_id = item.get('commentID')
        
        comment_dict = {
            'project_name': project_name,
            'comment_id': current_comment_id,
            
            # [추가/수정] 계층 구조 추적 컬럼
            'parent_id': actual_parent_id,        # 어느 댓글에 달렸는지 (원본은 None)
            'depth_level': current_depth,         # 0=원본, 1=대댓글, 2=대대댓글
            
            'author_id': author_id,
            'author_name': user_info.get('nickname', 'Unknown'),
            'creator_id': item.get('authorType', 0), 
            
            'is_pledge_master': badges_dict['is_pledge_master'],
            'is_backer': badges_dict['is_backer'],
            'backer_number': badges_dict['backer_number'],
            'is_prior_backer': badges_dict['is_prior_backer'],
            'is_pathfinder': badges_dict['is_pathfinder'],
            
            'has_children': bool(children_count > 0),
            'children_count': children_count,
            
            'text': item.get('text'),
            'created_at': item.get('createdAt'),
            'likes': item.get('likesCount')
        }
        extracted_data.append(comment_dict)
        
        # 대댓글(children)이 존재한다면, 깊이(depth)를 1 늘려서 자기 자신을 다시 호출(재귀)
        children_list = item.get('children')
        if children_list:
            extracted_data.extend(
                extract_comments_recursive(
                    items=children_list, 
                    user_mapping=user_mapping, 
                    project_name=project_name, 
                    current_depth=current_depth + 1,       # 깊이 + 1
                    fallback_parent_id=current_comment_id  # 현재 댓글이 부모가 됨
                )
            )
            
    return extracted_data

# 4. 단일 프로젝트 리뷰 수집기
def fetch_single_project_comments(project_name, thread_id, headers):
    comment_api_url = "https://gamefound.com/api/comments/getComments"
    author_api_url = "https://gamefound.com/api/comments/getCommentsAuthors"
    
    comment_list = []
    last_fetched_id = None
    
    while True:
        comment_payload = {
            "commentThreadID": thread_id, "sortType": 0,
            "lastFetchedCommentID": last_fetched_id, "GetCommentsForCurrentUser": False
        }
        res_comments = requests.post(comment_api_url, headers=headers, json=comment_payload)
        if res_comments.status_code != 200: break
            
        items = res_comments.json().get('data', {}).get('pagedItems', [])
        if not items: break
            
        # [수정] 대댓글을 포함한 '모든' 작성자 ID 추출
        author_ids = get_all_author_ids_recursive(items)
        
        user_mapping = {}
        if author_ids:
            author_payload = {"authorIDs": author_ids, "commentThreadID": thread_id}
            res_authors = requests.post(author_api_url, headers=headers, json=author_payload)
            if res_authors.status_code == 200:
                user_mapping = res_authors.json().get('data', {})

        # [수정] 재귀 함수를 통한 계층 구조 추출 병합
        parsed_comments = extract_comments_recursive(items, user_mapping, project_name, current_depth=0)
        comment_list.extend(parsed_comments)
        
        # 다음 페이지 호출을 위해, 가장 겉면에 있는 마지막 댓글 ID 갱신
        last_fetched_id = items[-1].get('commentID')
        time.sleep(1.0) 
        
    return comment_list

# 5. 전체 데이터 수집 컨트롤러
def run_mass_crawler(project_csv_path):
    if not os.path.exists(project_csv_path): return
    df_projects = pd.read_csv(project_csv_path)
    
    HEADERS = {
        "accept": "application/json", "content-type": "application/json",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    all_comments = []
    total_projects = len(df_projects)
    print(f"📊 총 {total_projects}개 보드게임 대상 리뷰 수집 시작...\n")
    
    try:
        for idx, row in df_projects.iterrows():
            p_name = row['name']
            p_url = row['project_url']
            if pd.isna(p_url): continue
                
            print(f"[{idx+1}/{total_projects}] '{p_name}' 분석 중...")
            thread_id = extract_thread_id_from_html(p_url, HEADERS)
            if not thread_id: continue
                
            comments = fetch_single_project_comments(p_name, thread_id, HEADERS)
            all_comments.extend(comments)
            print(f"  [+] {len(comments)}개 리뷰(대댓글 포함) 확보 (누적: {len(all_comments):,}개)")
            time.sleep(1.5)
            
    except KeyboardInterrupt:
        print("\n🚨 강제 중단 감지. 데이터 보존 중...")
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        
    if all_comments:
        save_dir = os.path.join(os.getcwd(), '02_Data', 'raw')
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, 'gamefound_ALL_comments_Hierarchical.csv')
        pd.DataFrame(all_comments).to_csv(save_path, index=False, encoding="utf-8-sig")
        print(f"\n✅ 전체 리뷰 병합 완료: {save_path} (총 {len(all_comments):,}건)")

if __name__ == "__main__":
    PROJECT_LIST_FILE = os.path.join(os.getcwd(), '02_Data', 'raw', 'gamefound_list.csv')
    run_mass_crawler(PROJECT_LIST_FILE)